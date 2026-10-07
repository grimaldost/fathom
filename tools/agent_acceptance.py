#!/usr/bin/env python
"""Check that a fresh Claude Code agent can use the installed fathom plugin unaided.

Each scenario spawns one headless Claude Code session, the subject, with a user's goal in
plain words and nothing else: no appended system prompt, and no fathom command, flag, path,
skill or MCP tool name in the prompt. Whatever the subject learns about fathom it learns
from what the plugin shows it: the skill, the slash commands and the MCP tools. By default
the subject runs under a configuration directory of its own that holds only the credential,
with the plugin loaded from where it is installed, so nothing else in the user's
configuration (their CLAUDE.md, other plugins, hooks, settings) reaches it.

The harness then judges each session three ways:

- what the session could see: the init event of its stream (an environment fact, reported
  apart from the agent's behaviour);
- what the session did: the tool calls in its stream, classified by the fathom surface each
  one used;
- what is true afterwards: the files in its workspace, the calls that reached the
  ``claude`` stub a no-spend scenario runs with, the real data root's state, and a
  ``fathom reconcile`` the harness runs itself.

No subject is given the real data root. A scenario that needs existing data gets a local
clone of it, with the clone's ``origin`` remote and its agent instruction files removed, and
the harness compares the real data root's git state, ignored files included, before and
after every subject. Workspaces live in directories of their own, apart from the output
directory, under names that say nothing about the test.

Repository tooling, not part of the engine. Run it from an engine checkout:

    uv run python tools/agent_acceptance.py --dry-run --data-root DIR
    uv run python tools/agent_acceptance.py --preflight-only --data-root DIR
    uv run python tools/agent_acceptance.py --data-root DIR [--scenarios S1,S2,S3]

``docs/agent-acceptance.md`` says what each scenario checks and how to read the verdict.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fathom import streams
from fathom.adapters.claude_cli import (
    cleanup_dir,
    env_for_agent_code,
    hidden_from_children,
    terminate_process_tree,
)
from fathom.smoke import forge_claude_shim, read_argv_log

ENGINE_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_FILE = Path(__file__).resolve().parent / "agent_acceptance_scenarios.toml"

EXIT_PASSED = 0
EXIT_FAILED = 1
EXIT_ENVIRONMENT = 2
EXIT_USAGE = 3

# What the plugin exposes, spelled the way the CLI reports it in the init event: the MCP
# server as `plugin:<plugin>:<server>`, its tools as `mcp__plugin_<plugin>_<server>__<tool>`,
# and the commands and the skill as `<plugin>:<name>`.
PLUGIN = "fathom"
SKILL = "fathom-eval"
MCP_SERVER_PREFIX = "plugin:fathom:"
MCP_TOOL_PREFIX = "mcp__plugin_fathom_fathom__"
# The plugin's commands, used when the plugin's own commands/ directory cannot be read.
DEFAULT_COMMANDS = ("plan", "reconcile", "report", "run", "smoke")
# Each MCP tool by the fathom operation it performs.
MCP_OPERATIONS = {"plan": "run --dry-run", "report": "report", "smoke": "smoke"}
# fathom's subcommands, as src/fathom/cli.py defines them.
SUBCOMMANDS = frozenset(
    {
        "init",
        "run",
        "stop",
        "void",
        "report",
        "validate",
        "verify-arming",
        "reconcile",
        "index",
        "smoke",
    }
)
PAID_RUN = "run"
DRY_RUN = "run --dry-run"
# Operations that spawn claude, so spend money: a run, the smoke gate, the arming check.
SPENDING_OPS = frozenset({PAID_RUN, "smoke", "verify-arming"})
SPEND_RAILS = ("--max-run-usd", "--max-spawn-usd", "--max-budget-usd")
# Surfaces whose calls execute fathom. A command call only expands the command's text; the
# engine runs in the Bash call that follows it, which is classified on its own.
EXECUTING = ("cli", "mcp")

# The lines fathom itself prints when an operation ran. A Bash result that is not an error
# proves nothing on its own: `... | tail` reports tail's exit status, not fathom's.
RECONCILE_MARK = re.compile(r"^RECONCILE: (?:OK|FAILED)\b.*$", re.MULTILINE)
PLAN_MARK = re.compile(r"^planned:\s+\d+ trials\b.*\bceiling: \$\d[\d,]*\.\d\d.*$", re.MULTILINE)
CEILING = re.compile(r"ceiling: \$(\d[\d,]*\.\d\d)")

# How far a measurement may overrun the budget its prompt states before its check fails,
# and before the harness stops the session.
BUDGET_SLACK = 1.5
# The per-spawn cap `fathom run` applies when no --max-spawn-usd is given.
ENGINE_SPAWN_CAP_USD = 5.0
# How often a running subject's ledgers are read for new spend.
WATCH_POLL_S = 10.0

DEFAULT_EFFORT = "high"
CONFIG_MODES = ("isolated", "user")
# The one file an isolated configuration directory gets, as fathom's own trial spawns get
# it (fathom.adapters.claude_cli.make_isolated_config).
CREDENTIAL_FILE = ".credentials.json"

# Permissions only: the subject is never shown these lists. ToolSearch loads the schema of
# a deferred tool; without it an MCP tool the CLI defers could be listed and never called.
# The CLI on Windows also registers a PowerShell tool. It is left out, as fathom's own arms
# leave it out, so a subject that reaches for it is refused and uses Bash.
ALLOWED_TOOLS = (
    "Bash",
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Skill",
    "SlashCommand",
    "ToolSearch",
    "mcp__plugin_fathom_fathom",
)
# Prefix rules, so a speed bump rather than a boundary: the subject also runs without
# GitHub credentials (GITHUB_CREDENTIAL_VARS, and an empty GH_CONFIG_DIR).
DISALLOWED_TOOLS = ("Bash(git push:*)", "Bash(gh:*)", "Bash(gh.exe:*)", "WebFetch", "WebSearch")
# The preflight session needs one MCP tool and nothing else. The rest that could change
# something is denied outright, so that allow rules in the user's own settings cannot
# give it to the session.
PREFLIGHT_DISALLOWED = ("Bash", "PowerShell", "Write", "Edit", "NotebookEdit")
# The init event cannot show that the MCP server works: a headless session does not wait
# for it, so a short one sees "pending" (MCP_CONNECTION_NONBLOCKING=false does not change
# that). One call can: from a directory with no data root, `plan` answers that none
# resolves, which spawns, spends and writes nothing. The preflight is not a scenario, so
# its prompt may name the tool.
PREFLIGHT_TOOL = MCP_TOOL_PREFIX + "plan"
PREFLIGHT_PROMPT = (
    "Call the plan tool of the fathom MCP server with bank set to probe, then reply with "
    "the value of the ok field it returns and nothing else."
)
PREFLIGHT_BUDGET_USD = 0.20
PREFLIGHT_TIMEOUT_S = 300

# Text no prompt may contain: each one would tell the subject how to use fathom.
FORBIDDEN_TERMS = (
    "/fathom:",
    "--dry-run",
    "fathom-eval",
    "mcp__",
    "python -m",
    "--home",
    "FATHOM_HOME",
    "fathom init",
    "fathom run",
)
# Text nothing else the subject is shown may contain (its working directory, the values the
# harness sets, the names in its workspace): it would tell the subject it is under test.
TEST_TERMS = ("acceptance",)

# Variables a running Claude Code session, or the app hosting it, sets for the processes it
# starts. A subject is meant to look like a session a user started in a terminal, so every
# name under these prefixes goes, except the few in SESSION_VARS_KEPT, which a terminal
# session has too: where the configuration lives, which shell to use, how to sign in, and
# how long to wait for an MCP server.
SESSION_VAR_PREFIXES = ("CLAUDE", "MCP_")
SESSION_VARS = frozenset({"DISABLE_MICROCOMPACT"})
SESSION_VARS_KEPT = frozenset(
    {
        "CLAUDE_CONFIG_DIR",
        "CLAUDE_CODE_GIT_BASH_PATH",
        "CLAUDE_CODE_USE_POWERSHELL_TOOL",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "MCP_TIMEOUT",
        "MCP_TOOL_TIMEOUT",
    }
)
# What `uv run` sets for the harness itself. With them, `fathom` and `python` in a
# subject's shell would be this checkout's engine instead of the plugin's.
UV_RUN_VARS = frozenset({"VIRTUAL_ENV", "UV_RUN_RECURSION_DEPTH"})
GITHUB_CREDENTIAL_VARS = frozenset(
    {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"}
)

# Event types the analysis reads; any other type is counted and skipped.
KNOWN_EVENTS = frozenset({"system", "assistant", "user", "result"})
# How much of a fathom-surface error the verdict keeps.
ERROR_EXCERPT = 300


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

WORKSPACES = ("clone", "empty")
_SCENARIO_KEYS = frozenset(
    {"name", "workspace", "fathom_home", "names_tool", "measurement_budget_usd", "checks", "prompt"}
)


@dataclasses.dataclass(frozen=True)
class Scenario:
    """One subject session, as the scenarios file declares it."""

    id: str
    name: str
    workspace: str  # "clone" | "empty"
    prompt: str
    checks: tuple[str, ...]
    fathom_home: bool = False  # FATHOM_HOME names the clone; otherwise it is unset
    names_tool: bool = True  # False: the prompt must not contain the word "fathom"
    measurement_budget_usd: float = 0.0

    @property
    def dirname(self) -> str:
        return f"{self.id}-{self.name}"

    @property
    def no_spend(self) -> bool:
        """The scenario must spend nothing on fathom, and runs with a ``claude`` stub."""
        return "no_spend" in self.checks

    @property
    def spend_limit_usd(self) -> float | None:
        """The new ledger spend past which the harness stops the subject: nothing at all in
        a no-spend scenario, the measurement budget with its slack in a measuring one, and
        no limit otherwise."""
        if self.no_spend:
            return 0.0
        if self.measurement_budget_usd > 0:
            return self.measurement_budget_usd * BUDGET_SLACK
        return None


def load_scenarios(text: str) -> list[Scenario]:
    """Parse the scenarios file. Raises ``ValueError`` naming the first problem found."""
    data = tomllib.loads(text)
    scenarios: list[Scenario] = []
    for sid, table in data.items():
        if not isinstance(table, dict):
            raise ValueError(f"{sid}: expected a table")
        unknown = sorted(set(table) - _SCENARIO_KEYS)
        if unknown:
            raise ValueError(f"{sid}: unknown keys {unknown}")
        name = table.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9-]+", name):
            raise ValueError(f"{sid}: name must be lower-case letters, digits and hyphens")
        workspace = table.get("workspace")
        if workspace not in WORKSPACES:
            raise ValueError(f"{sid}: workspace must be one of {list(WORKSPACES)}")
        prompt = table.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"{sid}: prompt is missing")
        home = table.get("fathom_home", "unset")
        if home not in ("clone", "unset"):
            raise ValueError(f"{sid}: fathom_home must be 'clone' or 'unset'")
        if home == "clone" and workspace != "clone":
            raise ValueError(f"{sid}: fathom_home = 'clone' needs workspace = 'clone'")
        names_tool = table.get("names_tool", True)
        if not isinstance(names_tool, bool):
            raise ValueError(f"{sid}: names_tool must be true or false")
        budget = table.get("measurement_budget_usd", 0.0)
        if isinstance(budget, bool) or not isinstance(budget, int | float) or budget < 0:
            raise ValueError(f"{sid}: measurement_budget_usd must be a number >= 0")
        checks = table.get("checks", [])
        if not isinstance(checks, list) or not all(isinstance(c, str) for c in checks):
            raise ValueError(f"{sid}: checks must be a list of check names")
        bad = [c for c in checks if c not in CHECKS]
        if bad:
            raise ValueError(f"{sid}: unknown checks {bad}; known: {sorted(CHECKS)}")
        if "measurement_within_budget" in checks and budget <= 0:
            raise ValueError(f"{sid}: measurement_within_budget needs measurement_budget_usd")
        if "no_spend" in checks and budget > 0:
            raise ValueError(f"{sid}: no_spend contradicts measurement_budget_usd")
        needs_clone = [c for c in checks if c in CLONE_CHECKS]
        if needs_clone and workspace != "clone":
            raise ValueError(f"{sid}: checks {needs_clone} need workspace = 'clone'")
        scenarios.append(
            Scenario(
                id=sid,
                name=name,
                workspace=workspace,
                prompt=prompt.strip(),
                checks=tuple(checks),
                fathom_home=home == "clone",
                names_tool=names_tool,
                measurement_budget_usd=float(budget),
            )
        )
    if not scenarios:
        raise ValueError("the scenarios file declares no scenario")
    return scenarios


def select_scenarios(scenarios: Sequence[Scenario], wanted: str | None) -> list[Scenario]:
    """The scenarios named in *wanted* (comma-separated ids, any case), in that order.

    ``None`` or an empty string selects every scenario in file order.
    """
    if not wanted or not wanted.strip():
        return list(scenarios)
    by_id = {s.id.upper(): s for s in scenarios}
    chosen: list[Scenario] = []
    for raw in wanted.split(","):
        key = raw.strip().upper()
        if not key:
            continue
        if key not in by_id:
            raise ValueError(f"unknown scenario {raw.strip()!r}; known: {sorted(by_id)}")
        if by_id[key] not in chosen:
            chosen.append(by_id[key])
    return chosen


def prompt_violations(scenario: Scenario) -> list[str]:
    """What in *scenario*'s prompt would tell the subject how to use fathom ([] when clean)."""
    low = scenario.prompt.lower()
    found = [f"contains {term!r}" for term in FORBIDDEN_TERMS if term.lower() in low]
    if not scenario.names_tool and "fathom" in low:
        found.append("names the tool ('fathom'), and this scenario must not")
    return found


def exposure_violations(
    scenario: Scenario,
    shown: Mapping[str, str],
    scenarios: Sequence[Scenario] = (),
) -> list[str]:
    """What else the subject is shown that would tell it it is under test ([] when clean).

    *shown* maps a label to text the subject sees besides its prompt: its working directory
    (which Claude Code puts in the system prompt), the values the harness sets in its
    environment, and the names at the top of its workspace. None may contain
    :data:`TEST_TERMS` or a scenario's name or id, and a scenario that must not name the
    tool may not be shown the word "fathom" either.
    """
    terms = [*TEST_TERMS, *(s.name for s in (*scenarios, scenario))]
    if not scenario.names_tool:
        terms.append(PLUGIN)
    ids = sorted({s.id for s in (*scenarios, scenario)})
    found: list[str] = []
    for label, text in shown.items():
        low = text.lower()
        for term in dict.fromkeys(terms):
            if term.lower() in low:
                found.append(f"{label} contains {term!r}")
        found += [f"{label} contains the scenario id {sid!r}" for sid in ids if mentions(text, sid)]
    return found


# ---------------------------------------------------------------------------
# The subject's environment, configuration and command line
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SubjectEnv:
    """The environment a subject starts with, and how it differs from the harness's own."""

    env: dict[str, str]
    unset: list[str]  # names removed from the base environment, without their values
    path_dropped: list[str]  # PATH entries withheld, in order
    set: dict[str, str]  # what the harness set itself
    path_added: list[str]  # entries the harness put first on PATH


def withheld_dirs(data_root: Path | None) -> list[Path]:
    """The directories no subject may learn of through its environment: the real data
    root, this engine checkout, and the virtual environment the harness runs in."""
    dirs = [ENGINE_ROOT]
    if data_root is not None:
        dirs.append(data_root)
    if sys.prefix != sys.base_prefix:
        dirs.append(Path(sys.prefix))
    return dirs


def _session_var(name: str) -> bool:
    upper = name.upper()
    if upper in SESSION_VARS_KEPT:
        return False
    return (
        upper.startswith(SESSION_VAR_PREFIXES)
        or upper in SESSION_VARS
        or upper in UV_RUN_VARS
        or upper in GITHUB_CREDENTIAL_VARS
    )


def _path_key(env: Mapping[str, str]) -> str:
    return next((k for k in env if k.upper() == "PATH"), "PATH")


def subject_env(
    base: Mapping[str, str],
    fathom_home: Path | None,
    *,
    hidden: Sequence[Path] = (),
    config_dir: Path | None = None,
    gh_config_dir: Path | None = None,
    path_prepend: Sequence[Path] = (),
) -> SubjectEnv:
    """The environment a subject starts with.

    Starts from :func:`fathom.adapters.claude_cli.env_for_agent_code`, the environment the
    engine gives its own trial spawns: every ``FATHOM_*`` variable, ``PWD``, ``OLDPWD`` and
    the billing and routing variables removed, and no variable whose value names one of the
    *hidden* directories (:func:`withheld_dirs`); a PATH entry inside one is dropped. Then
    the parent session's variables, what ``uv run`` set for the harness and the GitHub
    credentials go (:func:`_session_var`). Last, the harness sets ``FATHOM_HOME`` to
    *fathom_home* (left unset when it is ``None``), ``CLAUDE_CONFIG_DIR`` (with the claude.ai
    connectors turned off) and ``GH_CONFIG_DIR`` when given, and puts *path_prepend* first on
    PATH. Names are compared
    case-insensitively, as Windows compares them.
    """
    with hidden_from_children(*hidden):
        env = env_for_agent_code(base)
    for name in list(env):
        if _session_var(name):
            del env[name]
    removed = sorted(name for name in base if name not in env)
    key = _path_key(env)
    kept = set(env.get(key, "").split(os.pathsep))
    base_path = base.get(_path_key(base), "")
    dropped = [e for e in base_path.split(os.pathsep) if e and e not in kept]
    harness: dict[str, str] = {}
    if fathom_home is not None:
        harness["FATHOM_HOME"] = str(fathom_home)
    if config_dir is not None:
        harness["CLAUDE_CONFIG_DIR"] = str(config_dir)
        # The account's claude.ai connectors reach a session whatever its configuration
        # directory; an isolated subject is shown the plugin's MCP server only.
        harness["ENABLE_CLAUDEAI_MCP_SERVERS"] = "false"
    if gh_config_dir is not None:
        harness["GH_CONFIG_DIR"] = str(gh_config_dir)
    env.update(harness)
    added = [str(p) for p in path_prepend]
    if added:
        env[key] = os.pathsep.join([*added, env.get(key, "")]).rstrip(os.pathsep)
    return SubjectEnv(env=env, unset=removed, path_dropped=dropped, set=harness, path_added=added)


def subject_command(
    *,
    model: str,
    budget_usd: float,
    effort: str = DEFAULT_EFFORT,
    allowed: Sequence[str] = ALLOWED_TOOLS,
    disallowed: Sequence[str] = DISALLOWED_TOOLS,
    plugin_dirs: Sequence[str] = (),
) -> list[str]:
    """The ``claude`` argv for one subject. The prompt goes on stdin, as the engine's adapter
    sends it, so no variadic option can swallow it and no shell quoting touches it.

    No system prompt is appended. The effort is always passed, as the engine passes it,
    so the user's own settings do not decide it. An empty *allowed* list leaves every tool
    to the headless default-deny.
    """
    cmd = [
        "claude",
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--effort",
        effort,
        "--max-budget-usd",
        f"{budget_usd:g}",
        "--permission-mode",
        "acceptEdits",
        "--no-session-persistence",
    ]
    if allowed:
        cmd += ["--allowedTools", ",".join(allowed)]
    cmd += ["--disallowedTools", ",".join(disallowed)]
    for plugin_dir in plugin_dirs:
        cmd += ["--plugin-dir", str(plugin_dir)]
    return cmd


def format_command(cmd: Sequence[str]) -> str:
    """*cmd* as one line in the host shell's quoting."""
    return subprocess.list2cmdline(list(cmd)) if os.name == "nt" else shlex.join(cmd)


def real_config_dir(environ: Mapping[str, str]) -> Path:
    """The user's Claude Code configuration directory: ``CLAUDE_CONFIG_DIR``, else
    ``~/.claude``."""
    value = environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return Path(value) if value else Path.home() / ".claude"


def installed_plugin_path(config_dir: Path) -> Path | None:
    """Where the fathom plugin is installed, from the CLI's record of installed plugins
    (``plugins/installed_plugins.json``): a user-scope entry first, then the most recently
    updated. ``None`` when there is no record or the directory is gone."""
    try:
        data = json.loads(
            (config_dir / "plugins" / "installed_plugins.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return None
    plugins = data.get("plugins") if isinstance(data, dict) else None
    entries: list[dict[str, Any]] = []
    for key, value in (plugins or {}).items():
        if str(key).split("@", 1)[0] != PLUGIN:
            continue
        for entry in value if isinstance(value, list) else [value]:
            if isinstance(entry, dict) and isinstance(entry.get("installPath"), str):
                entries.append(entry)
    entries.sort(key=lambda e: (e.get("scope") == "user", str(e.get("lastUpdated") or "")))
    for entry in reversed(entries):
        path = Path(entry["installPath"])
        if path.is_dir():
            return path
    return None


# The memory files Claude Code reads in the working directory and in every directory
# above it, whatever its configuration directory says. On Windows the temporary directory
# lies inside the user's profile, so the profile's `.claude/CLAUDE.md`, the user's own
# instructions, is read as the memory of a directory above every workspace made there.
MEMORY_FILES = ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", "AGENTS.md")


def ancestor_instructions(directory: Path) -> list[Path]:
    """The instruction files in *directory* and in every directory above it, nearest first."""
    found: list[Path] = []
    for folder in (directory, *directory.parents):
        for name in MEMORY_FILES:
            path = folder / name
            with contextlib.suppress(OSError):
                if path.is_file():
                    found.append(path)
    return found


def default_workspace_base(temp: Path, environ: Mapping[str, str]) -> Path | None:
    """Where an isolated subject's workspace goes when ``--workspace-root`` is not given:
    the temporary directory when no instruction file lies at or above it, else the public
    profile directory (``%PUBLIC%`` on Windows) when none lies at or above that. ``None``
    when neither is clean, which the caller refuses."""
    candidates = [temp]
    if environ.get("PUBLIC"):
        candidates.append(Path(environ["PUBLIC"]))
    for candidate in candidates:
        if candidate.is_dir() and not ancestor_instructions(candidate):
            return candidate
    return None


def make_subject_config(real_config: Path, dest: Path) -> bool:
    """Fill *dest* the way fathom fills a trial spawn's configuration directory: with the
    credential file and nothing else. Its path names nothing (the engine's own prefix would
    name fathom). Returns whether the credential was there to copy."""
    dest.mkdir(parents=True, exist_ok=True)
    source = real_config / CREDENTIAL_FILE
    if not source.is_file():
        return False
    shutil.copy2(source, dest / CREDENTIAL_FILE)
    return True


def install_claude_stub(directory: Path) -> Path:
    """Put a ``claude`` in *directory* that records each call and spends nothing, and return
    the file it records to.

    It is the stub fathom's own smoke gate uses (:func:`fathom.smoke.forge_claude_shim`): a
    real ``claude.exe`` on Windows, since a bare ``claude`` resolves through CreateProcess,
    which tries only ``.exe``. First on a subject's PATH, it is what every ``claude`` the
    engine spawns for that subject reaches, through the CLI or the MCP server alike.
    """
    log = directory / "calls.jsonl"
    forge_claude_shim(directory, log)
    return log


# ---------------------------------------------------------------------------
# The data root
# ---------------------------------------------------------------------------


def data_root_problem(path: Path) -> str | None:
    """Why *path* cannot serve as the data root the harness clones (``None`` when it can).

    The harness refuses an engine checkout or plugin tree (a ``.claude-plugin/plugin.json``
    or a ``src/fathom/`` in it), a plugin cache directory, a directory whose ``fathom.toml``
    has no ``[data_root]`` table, and a directory that is not the top of a git work tree,
    since the clone is made with git.
    """
    if not path.is_dir():
        return f"{path} is not a directory"
    if (path / ".claude-plugin" / "plugin.json").is_file() or (path / "src" / "fathom").is_dir():
        return (
            f"{path} is an engine checkout or a plugin tree, not a data root. Pass the "
            "directory that holds your tasks/, scenarios/ and ledger/."
        )
    if "/plugins/cache/" in path.resolve().as_posix().lower() + "/":
        return f"{path} is inside a plugin cache directory, not a data root"
    config = path / "fathom.toml"
    if not config.is_file():
        return f"{path} has no fathom.toml, so it is not a data root"
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return f"{config} cannot be read as TOML ({exc})"
    if not isinstance(data.get("data_root"), dict):
        return f"{config} has no [data_root] table, so {path} is not a data root"
    if not (path / ".git").exists():
        return f"{path} is not the top of a git work tree; the harness clones it with git"
    return None


def resolve_data_root(given: Path | None, environ: Mapping[str, str]) -> Path | None:
    """``--data-root`` if given, else the parent's ``FATHOM_HOME`` (an empty value is unset)."""
    if given is not None:
        return given.resolve()
    value = environ.get("FATHOM_HOME", "").strip()
    return Path(value).resolve() if value else None


def ledger_banks(root: Path) -> list[str]:
    """The banks that have a ledger in *root* (``ledger/<bank>.jsonl``), sorted."""
    return sorted(p.stem for p in (root / "ledger").glob("*.jsonl"))


# Files that instruct an agent working in a directory. Claude Code loads a CLAUDE.md as
# soon as the agent reads a file beside or below it, so a clone that kept the data root's
# own would teach the subject fathom in place of the plugin.
INSTRUCTION_FILES = frozenset({"claude.md", "claude.local.md", "agents.md"})


def instruction_paths(tracked: Iterable[str]) -> list[str]:
    """The *tracked* paths (POSIX, relative) that instruct an agent: a CLAUDE.md,
    CLAUDE.local.md or AGENTS.md at any depth, and anything under a ``.claude/``."""
    found: list[str] = []
    for path in tracked:
        parts = path.split("/")
        if parts[-1].lower() in INSTRUCTION_FILES or ".claude" in parts[:-1]:
            found.append(path)
    return found


# ---------------------------------------------------------------------------
# Transcript analysis (pure)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Invocation:
    """One fathom operation a tool call asked for.

    ``op`` is a subcommand (``reconcile``), ``run --dry-run`` for any plan, ``run`` for a
    paid run, ``--help`` or ``--version``, or ``other``.
    """

    op: str
    args: tuple[str, ...] = ()


def _comparable(text: str) -> str:
    """*text* with forward slashes, and lower-cased on Windows, where paths ignore case."""
    text = text.replace("\\", "/")
    return text.lower() if os.name == "nt" else text


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def plain_text(text: str) -> str:
    """A tool result's text with the CLI's content-block wrapping undone: a JSON list of
    ``{"type": "text", "text": ...}`` blocks becomes their text."""
    try:
        blocks = json.loads(text)
    except ValueError:
        return text
    if isinstance(blocks, list) and blocks and all(isinstance(b, dict) for b in blocks):
        return "\n".join(str(b.get("text", "")) for b in blocks)
    return text


@dataclasses.dataclass
class ToolCall:
    """A ``tool_use`` from the stream, classified, with its paired result."""

    index: int
    id: str | None
    name: str
    summary: str
    surface: str | None  # skill | command | mcp | cli | docs | None (not fathom)
    invocations: list[Invocation]
    result: dict[str, Any] | None = None  # {"tool_use_id", "is_error", "text"}
    input: dict[str, Any] = dataclasses.field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return bool(self.result and self.result["is_error"])

    @property
    def text(self) -> str:
        return plain_text(str(self.result["text"])) if self.result else ""

    @property
    def input_text(self) -> str:
        """Every string in the call's input, in :func:`_comparable` form."""
        return _comparable("\n".join(_strings(self.input)))

    @property
    def answered(self) -> bool:
        """A result came back and is not an error: for an MCP call, the server is up, whatever
        its ``ok`` says."""
        return self.result is not None and not self.is_error

    @property
    def succeeded(self) -> bool:
        """A result came back, it is not an error, and an MCP result does not say ``ok`` false.

        For a CLI call this says only that the shell's last command exited 0; whether
        fathom ran is :func:`marker_line`'s question.
        """
        if self.result is None or self.is_error:
            return False
        return not (self.surface == "mcp" and re.search(r'\\?"ok\\?":\s*false', self.text))


def marker_line(call: ToolCall, op: str) -> str | None:
    """The line fathom printed when *call* ran operation *op* (a reconcile's ``RECONCILE:``
    line, a plan's ``planned: ... ceiling:`` line), or ``None`` when there is none."""
    pattern = {"reconcile": RECONCILE_MARK, DRY_RUN: PLAN_MARK}.get(op)
    if pattern is None or call.result is None:
        return None
    match = pattern.search(call.text)
    return match.group(0).strip() if match else None


@dataclasses.dataclass
class Analysis:
    """What one subject's stream shows."""

    init: dict[str, Any] | None
    calls: list[ToolCall]
    result: dict[str, Any] | None
    malformed_lines: int = 0
    other_events: int = 0
    closing_text: str = ""  # the assistant's text after its last tool call

    @property
    def fathom_calls(self) -> list[ToolCall]:
        return [c for c in self.calls if c.surface]

    @property
    def first_fathom_index(self) -> int | None:
        """The index of the first fathom call: how many tool calls came before it."""
        return next((c.index for c in self.calls if c.surface), None)

    def executed(self, op: str) -> list[ToolCall]:
        """Calls that executed fathom operation *op* (CLI or MCP), in order."""
        return [
            c
            for c in self.calls
            if c.surface in EXECUTING and any(inv.op == op for inv in c.invocations)
        ]

    @property
    def answer(self) -> str:
        """The final answer: the result event's text and the assistant's closing text."""
        final = str((self.result or {}).get("result") or "")
        return "\n".join(t for t in (final, self.closing_text) if t)


def parse_lines(lines: Iterable[str]) -> tuple[list[dict[str, Any]], int]:
    """The JSON-object events in *lines*, and how many non-blank lines were not one."""
    events: list[dict[str, Any]] = []
    malformed = 0
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        # An event whose message is not an object is JSON but not an event the CLI emits.
        if isinstance(obj, dict) and isinstance(obj.get("message", {}), dict):
            events.append(obj)
        else:
            malformed += 1
    return events, malformed


def _init_list(init: Mapping[str, Any] | None, key: str) -> list[Any]:
    value = init.get(key) if init else None
    return list(value) if isinstance(value, list) else []


def fathom_plugins(init: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """The init event's plugin entries for fathom (``{"name", "path", "version", ...}``).

    More than one when ``--plugin-dir`` loads a development tree beside the installed copy.
    """
    return [
        p for p in _init_list(init, "plugins") if isinstance(p, dict) and p.get("name") == PLUGIN
    ]


def commands_from_init(init: Mapping[str, Any] | None) -> tuple[str, ...]:
    """The plugin's command names the init event lists (its skill names excluded)."""
    prefix = f"{PLUGIN}:"
    listed = [str(n) for n in _init_list(init, "slash_commands") if str(n).startswith(prefix)]
    skills = {str(n) for n in _init_list(init, "skills")}
    return tuple(sorted(n[len(prefix) :] for n in listed if n not in skills))


def _closing_text(events: Sequence[dict[str, Any]]) -> str:
    texts: list[str] = []
    for ev in events:
        if ev.get("type") != "assistant":
            continue
        content = (ev.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                texts = []
            elif block.get("type") == "text" and isinstance(block.get("text"), str):
                texts.append(block["text"])
    return "\n".join(texts)


def analyze(lines: Iterable[str], *, doc_roots: Sequence[str] = ()) -> Analysis:
    """Analyse a stream-json transcript. Never raises on content: an unknown event type or
    a malformed line is counted and skipped.

    *doc_roots* are directories whose files count as the plugin's documentation, beside
    the plugin paths the init event reports.
    """
    events, malformed = parse_lines(lines)
    init = streams.find_init(events)
    commands = commands_from_init(init) or DEFAULT_COMMANDS
    roots = [str(p["path"]) for p in fathom_plugins(init) if p.get("path")]
    roots += [str(r) for r in doc_roots]
    results = {
        r["tool_use_id"]: r
        for r in streams.tool_results(events)
        if isinstance(r["tool_use_id"], str)
    }
    calls: list[ToolCall] = []
    for index, use in enumerate(streams.tool_uses(events)):
        surface, invocations = classify(
            use["name"], use["input"], commands=commands, doc_roots=roots
        )
        calls.append(
            ToolCall(
                index=index,
                id=use["id"],
                name=use["name"],
                summary=summarize(use["name"], use["input"]),
                surface=surface,
                invocations=invocations,
                result=results.get(use["id"]) if isinstance(use["id"], str) else None,
                input=use["input"] if isinstance(use["input"], dict) else {},
            )
        )
    result = next((ev for ev in reversed(events) if ev.get("type") == "result"), None)
    other = sum(1 for ev in events if ev.get("type") not in KNOWN_EVENTS)
    return Analysis(
        init=init,
        calls=calls,
        result=result,
        malformed_lines=malformed,
        other_events=other,
        closing_text=_closing_text(events),
    )


def summarize(name: str, tool_input: Any, limit: int = 160) -> str:
    """A one-line description of a tool call's input."""
    inp = tool_input if isinstance(tool_input, dict) else {}
    if name in ("Bash", "PowerShell"):
        text = str(inp.get("command", ""))
    elif name in ("Read", "Write", "Edit"):
        text = str(inp.get("file_path", ""))
    elif name in ("Skill", "SlashCommand"):
        text = " ".join(str(inp.get(k, "")) for k in ("skill", "command", "args")).strip()
    else:
        text = json.dumps(inp, ensure_ascii=False, sort_keys=True)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def classify(
    name: str,
    tool_input: Any,
    *,
    commands: Sequence[str] = DEFAULT_COMMANDS,
    doc_roots: Sequence[str] = (),
) -> tuple[str | None, list[Invocation]]:
    """The fathom surface a tool call used, and the fathom operations it asked for.

    - ``mcp``: a tool of the plugin's MCP server;
    - ``command``: a Skill or SlashCommand call naming one of the plugin's *commands*
      (``fathom:plan``, ``/fathom:run ...``);
    - ``skill``: a Skill call naming anything else that starts with ``fathom``;
    - ``cli``: a Bash (or PowerShell) command that invokes fathom (:func:`cli_invocations`);
    - ``docs``: a Read of a file under the plugin's tree or ``skills/fathom-eval/``;
    - ``None``: not a fathom surface.
    """
    inp = tool_input if isinstance(tool_input, dict) else {}
    if name.startswith(MCP_TOOL_PREFIX):
        tool = name[len(MCP_TOOL_PREFIX) :]
        return "mcp", [Invocation(MCP_OPERATIONS.get(tool, "other"))]
    if name in ("Skill", "SlashCommand"):
        text = str(inp.get("skill") or inp.get("command") or "").strip()
        head, _, rest = text.partition(" ")
        head = head.lstrip("/")
        args = " ".join(part for part in (rest, str(inp.get("args") or "")) if part.strip())
        if head.startswith(f"{PLUGIN}:") and head.split(":", 1)[1] in commands:
            return "command", [command_invocation(head.split(":", 1)[1], args)]
        if head.startswith(PLUGIN):
            return "skill", []
        return None, []
    if name in ("Bash", "PowerShell"):
        invocations = cli_invocations(str(inp.get("command") or ""))
        return ("cli", invocations) if invocations else (None, [])
    if name == "Read" and is_plugin_doc(str(inp.get("file_path") or ""), doc_roots):
        return "docs", []
    return None, []


def command_invocation(command: str, args: str) -> Invocation:
    """The operation a plugin command performs with *args*."""
    argv = tuple(_split(args))
    if command == "plan" or (command == "run" and "--dry-run" in argv):
        return Invocation(DRY_RUN, argv)
    return Invocation(command, argv)


_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Command words that run the command after them: their options are skipped, and so is
# timeout's duration.
_WRAPPERS = frozenset({"env", "time", "exec", "command", "nohup", "call", "nice", "timeout"})
_UV_VALUE_OPTIONS = frozenset(
    {
        "--project",
        "--directory",
        "--with",
        "--with-editable",
        "--with-requirements",
        "--python",
        "-p",
        "--from",
        "--env-file",
        "--package",
        "--index",
        "--extra",
        "--group",
        "--only-group",
        "--cache-dir",
        "--config-file",
    }
)
_HEREDOC = re.compile(r"""(['"]?)([^\s;&|<>()'"]+)\1""")


def shell_segments(command: str) -> list[str]:
    """The simple commands in a shell command line, as text.

    The line is cut at the control operators outside quotes (``;``, ``&``, ``&&``, ``|``,
    ``||``), at parentheses and backquotes, and at newlines. A here-document's body and a
    comment are dropped, and a quoted string stays whole, so text that only mentions fathom
    (a heredoc that writes notes, an ``echo``, a commit message) is never read as a
    command. A redirection that names a descriptor (``2>&1``, ``&>file``) is not a cut.
    A command substitution inside double quotes is not looked into.
    """
    segments: list[str] = []
    buf: list[str] = []
    heredocs: list[tuple[str, bool]] = []
    quote: str | None = None
    i, n = 0, len(command)

    def cut() -> None:
        text = "".join(buf).strip()
        if text:
            segments.append(text)
        buf.clear()

    while i < n:
        ch = command[i]
        if quote is not None:
            buf.append(ch)
            if quote == '"' and ch == "\\" and i + 1 < n:
                buf.append(command[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            if command[i + 1] != "\n":  # a backslash-newline joins two lines
                buf += [ch, command[i + 1]]
            i += 2
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "#" and (not buf or buf[-1].isspace()):
            while i < n and command[i] != "\n":
                i += 1
            continue
        if command.startswith("<<<", i):  # a here-string: the text that follows is one word
            buf.append("<<<")
            i += 3
            continue
        if command.startswith("<<", i):
            j = i + 2
            strip_tabs = j < n and command[j] == "-"
            j += 1 if strip_tabs else 0
            while j < n and command[j] in " \t":
                j += 1
            match = _HEREDOC.match(command, j)
            if match:
                heredocs.append((match.group(2), strip_tabs))
                buf.append(command[i : match.end()])
                i = match.end()
                continue
        if ch == "\n":
            cut()
            i += 1
            for word, strip_tabs in heredocs:
                while i < n:
                    end = command.find("\n", i)
                    line = command[i : end if end != -1 else n].rstrip("\r")
                    i = end + 1 if end != -1 else n
                    if (line.lstrip("\t") if strip_tabs else line) == word:
                        break
            heredocs.clear()
            continue
        if ch in ";|&()`":
            prev = buf[-1] if buf else ""
            following = command[i + 1] if i + 1 < n else ""
            descriptor = (ch == "&" and (prev in ("<", ">") or following == ">")) or (
                ch == "|" and prev == ">"
            )
            if descriptor:
                buf.append(ch)
            else:
                cut()
            i += 1
            continue
        buf.append(ch)
        i += 1
    cut()
    return segments


def _split(text: str) -> list[str]:
    try:
        return shlex.split(text)
    except ValueError:  # an unbalanced quote: fall back to whitespace
        return text.split()


def _program(token: str) -> str:
    """A command word reduced to its program name: no directory, no ``.exe``, lower case."""
    name = re.split(r"[\\/]", token.strip("(){}"))[-1].lower()
    return name.removesuffix(".exe")


def _command_start(tokens: Sequence[str]) -> int:
    """The index of a segment's command word, past assignments and wrappers."""
    i = 0
    while i < len(tokens):
        if _ASSIGNMENT.match(tokens[i]):
            i += 1
            continue
        word = _program(tokens[i])
        if word not in _WRAPPERS:
            break
        i += 1
        while i < len(tokens) and tokens[i].startswith("-"):
            i += 1
        if word == "timeout" and i < len(tokens):
            i += 1  # the duration
    return i


def _shell_payload(tokens: Sequence[str]) -> str | None:
    """The command line a segment hands to another shell (``bash -c``, ``cmd /c``,
    ``pwsh -Command``), or ``None``."""
    i = _command_start(tokens)
    if i >= len(tokens):
        return None
    program, rest = _program(tokens[i]), list(tokens[i + 1 :])
    if program in ("bash", "sh", "zsh", "dash"):
        for j, token in enumerate(rest):
            if not token.startswith("-"):
                return None
            if not token.startswith("--") and "c" in token[1:]:
                return rest[j + 1] if j + 1 < len(rest) else None
        return None
    if program == "cmd":
        for j, token in enumerate(rest):
            if token.lower() in ("/c", "/k"):
                return " ".join(rest[j + 1 :])
        return None
    if program in ("pwsh", "powershell"):
        for j, token in enumerate(rest):
            low = token.lower()
            if low in ("-c", "-command") or (len(low) > 2 and "-command".startswith(low)):
                return " ".join(rest[j + 1 :])
        return None
    return None


def _skip_options(tokens: Sequence[str], j: int) -> int:
    while j < len(tokens) and tokens[j].startswith("-"):
        j += 2 if tokens[j] in _UV_VALUE_OPTIONS else 1
    return j


def _fathom_argv(tokens: Sequence[str]) -> list[str] | None:
    """The arguments after fathom's entry point in one shell segment, or ``None``.

    The entry point is ``-m fathom`` after a Python interpreter (``python -m fathom``,
    ``uv run ... python -m fathom``), a command word that is the ``fathom`` executable, or
    ``fathom`` launched by ``uv run``, ``uv tool run`` or ``uvx``, with uv's own options
    allowed before and after ``run``.
    """
    for i in range(len(tokens) - 1):
        if (
            tokens[i] == "-m"
            and tokens[i + 1] == PLUGIN
            and any(_program(t).startswith("python") or _program(t) == "py" for t in tokens[:i])
        ):
            return list(tokens[i + 2 :])
    i = _command_start(tokens)
    if i >= len(tokens):
        return None
    program = _program(tokens[i])
    if program == PLUGIN:
        return list(tokens[i + 1 :])
    if program not in ("uv", "uvx"):
        return None
    j = i + 1
    if program == "uv":
        j = _skip_options(tokens, j)
        if j < len(tokens) and tokens[j] == "tool":
            j = _skip_options(tokens, j + 1)
        if j >= len(tokens) or tokens[j] != "run":
            return None
        j += 1
    j = _skip_options(tokens, j)
    if j < len(tokens) and _program(tokens[j]) == PLUGIN:
        return list(tokens[j + 1 :])
    return None


def cli_invocation(argv: Sequence[str]) -> Invocation:
    """The operation of a fathom argv (everything after the entry point)."""
    args = tuple(argv)
    if "-h" in args or "--help" in args:
        return Invocation("--help", args)
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--version":
            return Invocation("--version", args)
        if arg == "--home":
            i += 2
        elif arg.startswith("-"):
            i += 1
        else:
            break
    if i >= len(args):
        return Invocation("other", args)
    sub, rest = args[i], args[i + 1 :]
    if sub == "run" and "--dry-run" in rest:
        return Invocation(DRY_RUN, args)
    return Invocation(sub if sub in SUBCOMMANDS else "other", args)


# A shell function definition, `name() { body; }` or `function name { body; }`.
_FUNCTION_DEF = re.compile(
    r"(?:\bfunction\s+([A-Za-z_][\w-]*)\s*(?:\(\s*\))?|\b([A-Za-z_][\w-]*)\s*\(\s*\))"
    r"\s*\{([^{}]*)\}"
)
# A command word that is a variable's value: `$F`, `${F}` (quotes are gone after _split).
_EXPANSION = re.compile(r"^\$(?:\{([A-Za-z_]\w*)\}|([A-Za-z_]\w*))$")
_ALL_ARGS = frozenset({"$@", "$*", "${@}", "${*}"})


def _shell_functions(command: str) -> tuple[str, dict[str, list[str]]]:
    """The command line without the definitions of functions whose body runs fathom, and
    those bodies as tokens, by function name."""
    functions: dict[str, list[str]] = {}

    def record(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        for segment in shell_segments(match.group(3)):
            tokens = _split(segment)
            if _fathom_argv(tokens) is not None:
                functions[name] = tokens
                return " "
        return match.group(0)

    return _FUNCTION_DEF.sub(record, command), functions


def _expand_alias(
    tokens: list[str], variables: Mapping[str, list[str]], functions: Mapping[str, list[str]]
) -> list[str]:
    """*tokens* with a command word that names a fathom variable or function replaced by
    what it stands for, the function's ``"$@"`` by the call's arguments."""
    start = _command_start(tokens)
    if start >= len(tokens):
        return tokens
    head, word, args = tokens[:start], tokens[start], tokens[start + 1 :]
    match = _EXPANSION.match(word)
    name = match and (match.group(1) or match.group(2))
    if name and name in variables:
        return [*head, *variables[name], *args]
    if word in functions:
        body = functions[word]
        if any(t in _ALL_ARGS for t in body):
            return [*head, *(x for t in body for x in (args if t in _ALL_ARGS else [t]))]
        return [*head, *body, *args]
    return tokens


def cli_invocations(command: str, _depth: int = 0) -> list[Invocation]:
    """Every fathom invocation in a shell command line, in order ([] when there is none).

    The line is cut into simple commands (:func:`shell_segments`) and each is read as one
    command; a command line handed to another shell (``bash -c``, ``cmd /c``) is read in
    turn. A word that merely contains "fathom" (a path, a grep pattern, a quoted string)
    is not an invocation. Agents often keep the long plugin invocation in a variable
    (``F="uv run ... python -m fathom"; $F run b``) or a function
    (``F() { uv run ... python -m fathom "$@"; }; F run b``); a call through either is read
    as the command it stands for, and the definition itself is not an invocation.
    """
    command, functions = _shell_functions(command)
    variables: dict[str, list[str]] = {}
    out: list[Invocation] = []
    for segment in shell_segments(command):
        tokens = _split(segment)
        if tokens and all(_ASSIGNMENT.match(t) for t in tokens):
            for token in tokens:
                name, _, value = token.partition("=")
                value_tokens = _split(value)
                if _fathom_argv(value_tokens) is not None:
                    variables[name] = value_tokens
                else:
                    variables.pop(name, None)
            continue
        tokens = _expand_alias(tokens, variables, functions)
        payload = _shell_payload(tokens)
        if payload is not None:
            if _depth < 3:
                out += cli_invocations(payload, _depth + 1)
            continue
        argv = _fathom_argv(tokens)
        if argv is not None:
            out.append(cli_invocation(argv))
    return out


_REDIRECT = re.compile(r"^\d*(?:>\||&>>?|>>?)(.*)$")


def redirect_targets(command: str) -> list[str]:
    """The files a shell command line writes through ``>``, ``>>`` or ``tee``."""
    targets: list[str] = []
    for segment in shell_segments(command):
        tokens = _split(segment)
        for j, token in enumerate(tokens):
            match = _REDIRECT.match(token)
            if match:
                target = match.group(1) or (tokens[j + 1] if j + 1 < len(tokens) else "")
                if target and not target.startswith("&"):
                    targets.append(target)
        start = _command_start(tokens)
        if start < len(tokens) and _program(tokens[start]) == "tee":
            targets += [t for t in tokens[start + 1 :] if not t.startswith("-")]
    return targets


_PLUGIN_CACHE = re.compile(r"/plugins/cache/[^/]+/fathom/")


def is_plugin_doc(path: str, doc_roots: Sequence[str] = ()) -> bool:
    """Whether *path* lies in the fathom plugin's tree: a plugin cache copy, a
    ``skills/fathom-eval/`` directory, or one of *doc_roots*."""
    norm = path.replace("\\", "/").lower()
    if f"skills/{SKILL}/" in norm or _PLUGIN_CACHE.search(norm):
        return True
    for root in doc_roots:
        base = root.replace("\\", "/").lower().rstrip("/")
        if base and norm.startswith(base + "/"):
            return True
    return False


@dataclasses.dataclass
class Visibility:
    """What the subject could see of the plugin when its session started."""

    init_seen: bool
    mcp_servers: list[str]  # "name=status" for the plugin's servers
    mcp_connected: bool
    mcp_connected_late: bool  # pending at init, then a call it answered
    mcp_unconfirmed: bool  # pending at init, and no call to one of its tools was answered
    commands_listed: list[str]
    commands_missing: list[str]
    skill_listed: bool
    plugins: list[dict[str, Any]]

    @property
    def ok(self) -> bool:
        return not self.problems()

    def problems(self) -> list[str]:
        if not self.init_seen:
            return ["the stream has no init event"]
        out: list[str] = []
        if not self.mcp_connected and not self.mcp_unconfirmed:
            seen = ", ".join(self.mcp_servers) or "not listed"
            out.append(f"the fathom MCP server is not connected ({seen})")
        if self.commands_missing:
            out.append(f"commands not listed: {', '.join(self.commands_missing)}")
        if not self.skill_listed:
            out.append(f"the {SKILL} skill is not listed")
        return out


def assess_visibility(
    analysis: Analysis, expected_commands: Sequence[str] = DEFAULT_COMMANDS
) -> Visibility:
    """Whether the plugin's MCP server is connected, its commands listed and its skill listed.

    A server still pending in the init event counts as connected when a later call to one
    of its tools was answered (an ``ok`` false answer included), and as unconfirmed, which
    is not a problem, when none was: a headless session starts before its servers connect,
    so a subject that never calls the server leaves it pending. The preflight is what
    proves the connection. Only a server
    that failed, needs authentication or is not listed is an environment failure.
    """
    init = analysis.init
    servers = [
        s
        for s in _init_list(init, "mcp_servers")
        if isinstance(s, dict) and str(s.get("name", "")).startswith(MCP_SERVER_PREFIX)
    ]
    statuses = {str(s.get("status", "")).lower() for s in servers}
    at_init = "connected" in statuses
    pending = "pending" in statuses
    later = any(c.surface == "mcp" and c.answered for c in analysis.calls)
    prefix = f"{PLUGIN}:"
    listed = sorted(
        str(n)[len(prefix) :]
        for n in _init_list(init, "slash_commands")
        if str(n).startswith(prefix)
    )
    skills = {str(s) for s in _init_list(init, "skills")}
    plugins = fathom_plugins(init)
    return Visibility(
        init_seen=analysis.init is not None,
        mcp_servers=[f"{s.get('name')}={s.get('status')}" for s in servers],
        mcp_connected=at_init or later,
        mcp_connected_late=later and not at_init,
        mcp_unconfirmed=pending and not (at_init or later),
        commands_listed=listed,
        commands_missing=[c for c in expected_commands if c not in listed],
        skill_listed=f"{PLUGIN}:{SKILL}" in skills or SKILL in skills,
        plugins=plugins,
    )


def plan_ceilings(analysis: Analysis) -> list[str]:
    """The USD ceilings (``"12.50"``) the plans in the stream printed."""
    found: list[str] = []
    for call in analysis.executed(DRY_RUN):
        if call.surface == "mcp" and not call.succeeded:
            continue
        for value in CEILING.findall(call.text):
            if value not in found:
                found.append(value)
    return found


def behaviour(analysis: Analysis) -> dict[str, Any]:
    """Informational facts about how the subject used fathom; none of them is pass/fail.

    ``smoke_before_run``, ``plan_before_run`` and ``budget_rail_used`` are ``None`` when the
    subject made no paid run; ``answer_quotes_plan_ceiling`` is ``None`` when no plan
    printed a ceiling. It is not a check, since prose rounds ("about $5").
    """
    ops = [(c.index, c.surface, inv) for c in analysis.calls if c.surface for inv in c.invocations]
    executing = [(i, inv) for i, surface, inv in ops if surface in EXECUTING]
    paid = [(i, inv) for i, inv in executing if inv.op == PAID_RUN]
    first_paid = paid[0][0] if paid else None

    def before_first_paid(op: str) -> bool | None:
        if first_paid is None:
            return None
        return any(i < first_paid and inv.op == op for i, inv in executing)

    first = analysis.first_fathom_index
    first_call = analysis.calls[first] if first is not None else None
    surfaces: list[str] = []
    for call in analysis.fathom_calls:
        if call.surface and call.surface not in surfaces:
            surfaces.append(call.surface)
    ceilings = plan_ceilings(analysis)
    answer = analysis.answer
    return {
        "tool_calls": len(analysis.calls),
        "surfaces_used": surfaces,
        "first_fathom_use_index": first,
        "first_fathom_use": (
            f"#{first_call.index} {first_call.surface}: {first_call.summary}"
            if first_call
            else None
        ),
        "operations": [f"#{i} {s}: {inv.op}" for i, s, inv in ops],
        "paid_runs": len(paid),
        "spending_operations": [f"#{i} {inv.op}" for i, inv in executing if inv.op in SPENDING_OPS],
        "budget_rail_used": (
            any(a.split("=", 1)[0] in SPEND_RAILS for _, inv in paid for a in inv.args)
            if paid
            else None
        ),
        "smoke_before_run": before_first_paid("smoke"),
        "plan_before_run": before_first_paid(DRY_RUN),
        "plan_ceilings_usd": ceilings,
        "answer_quotes_plan_ceiling": (
            any(c in answer or c.replace(",", "") in answer for c in ceilings) if ceilings else None
        ),
    }


def fathom_errors(analysis: Analysis) -> list[dict[str, Any]]:
    """The fathom-surface calls whose result was an error, with an excerpt of each."""
    return [
        {"index": c.index, "surface": c.surface, "tool": c.name, "text": c.text[:ERROR_EXCERPT]}
        for c in analysis.fathom_calls
        if c.is_error
    ]


# Result files a subject must not write itself: a ledger and a rendered scorecard.
_RESULT_FILE = re.compile(
    r"(?:^|/)(?:ledger[^/]*/[^/]+\.jsonl|report/scorecard-[^/]+\.md)$", re.IGNORECASE
)
_WRITING_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def hand_written_results(analysis: Analysis) -> list[str]:
    """Tool calls that wrote a ledger or a scorecard directly instead of through fathom: a
    Write or Edit of one, or a shell redirection or ``tee`` into one."""
    found: list[str] = []
    for call in analysis.calls:
        if call.name in _WRITING_TOOLS:
            path = str(call.input.get("file_path") or call.input.get("notebook_path") or "")
            if _RESULT_FILE.search(path.replace("\\", "/")):
                found.append(f"#{call.index} {call.name} {path}")
        elif call.name in ("Bash", "PowerShell"):
            for target in redirect_targets(str(call.input.get("command") or "")):
                if _RESULT_FILE.search(target.replace("\\", "/")):
                    found.append(f"#{call.index} {call.name} writes {target}")
    return found


def session_facts(init: Mapping[str, Any] | None) -> dict[str, Any]:
    """What the init event says about the subject's session, for the verdict."""
    init = init or {}
    return {
        key: init.get(key)
        for key in (
            "claude_code_version",
            "model",
            "permissionMode",
            "cwd",
            "memory_paths",
            "tools",
            "mcp_servers",
            "slash_commands",
            "skills",
            "plugins",
        )
    }


# ---------------------------------------------------------------------------
# Ground truth (pure scans of files and of git's output)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GitState:
    head: str
    status: str  # `git status --porcelain=v1 -z --untracked-files=all --ignored`
    # (path, size, mtime in ns) of each ignored file, which git status lists but does not
    # compare: a write to report/ or a local cache shows only here.
    ignored: tuple[tuple[str, int, int], ...] = ()


@dataclasses.dataclass(frozen=True)
class Outcome:
    """A command the harness ran itself."""

    exit_code: int | None
    output: str


@dataclasses.dataclass
class RootScan:
    """A data root found under a workspace, and what it holds.

    Ledger rows the workspace started with, and rows identical to the ones the plugin's
    own example data root ships, are not the subject's and are left out of every count.
    """

    path: Path
    banks: list[str]
    tasks: list[str]  # "<bank>/<task>"
    tasks_with_verifier: list[str]
    arms: list[str]  # TOML files declaring a strategy, relative to the root
    completed_trials: int  # the subject's completed trials of a task that has its verifier
    configs: list[str]  # distinct config_hash values of those trials
    engine_written: int  # those trials whose rows carry what only the engine writes
    run_rows: int
    spend_usd: float  # cost_usd_est summed over the subject's rows
    scorecards: list[str]
    excluded_rows: int = 0  # rows left out as not the subject's


def porcelain_paths(raw: str) -> list[str]:
    """The paths in ``git status --porcelain=v1 -z`` output; a rename yields both paths."""
    entries = raw.split("\0")
    paths: list[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC" and i < len(entries) and entries[i]:
            paths.append(entries[i])
            i += 1
    return paths


def ignored_paths(raw: str) -> list[str]:
    """The ignored paths (``!!`` entries) in ``git status --porcelain=v1 -z --ignored``."""
    return [entry[3:] for entry in raw.split("\0") if entry.startswith("!! ")]


def ledger_changes(paths: Iterable[str]) -> list[str]:
    """The *paths* under a top-level ``ledger*/`` directory."""
    return [p for p in paths if p.replace("\\", "/").split("/", 1)[0].startswith("ledger")]


def _ignored(path: str) -> bool:
    return path.replace("\\", "/").startswith(("report/", ".fathom/"))


def mentions(text: str, name: str) -> bool:
    """Whether *text* names *name* as a whole word (``bank-a`` is not in ``bank-a-extended``)."""
    pattern = rf"(?<![A-Za-z0-9_-]){re.escape(name)}(?![A-Za-z0-9_-])"
    return re.search(pattern, text, re.IGNORECASE) is not None


_SCAN_SKIP = frozenset({".git", ".venv", "node_modules", "__pycache__", ".fathom"})
_ARM_SKIP = frozenset({"tasks", "ledger", "report"}) | _SCAN_SKIP


def _read_toml(path: Path) -> dict[str, Any] | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None


def find_data_roots(workspace: Path, *, max_depth: int | None = None) -> list[Path]:
    """Directories under *workspace* (itself included, at most *max_depth* levels down)
    whose ``fathom.toml`` has a ``[data_root]`` table, shallowest first."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(workspace):
        depth = len(Path(dirpath).relative_to(workspace).parts)
        if max_depth is not None and depth >= max_depth:
            dirnames[:] = []
        dirnames[:] = sorted(d for d in dirnames if d not in _SCAN_SKIP)
        if "fathom.toml" in filenames:
            data = _read_toml(Path(dirpath) / "fathom.toml")
            if data is not None and isinstance(data.get("data_root"), dict):
                found.append(Path(dirpath))
    return sorted(found, key=lambda p: (len(p.parts), str(p)))


def canonical_row(row: Mapping[str, Any]) -> str:
    """A ledger row as one comparable string, whatever the spacing of its line."""
    return json.dumps(row, sort_keys=True, ensure_ascii=False)


def ledger_rows(root: Path) -> list[dict[str, Any]]:
    """The rows of every ``ledger/*.jsonl`` in *root*."""
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "ledger").glob("*.jsonl")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        events, _ = parse_lines(text.splitlines())
        rows.extend(events)
    return rows


def example_rows(plugin_roots: Iterable[Path]) -> frozenset[str]:
    """The ledger rows the plugin ships as examples (``examples/**/ledger/*.jsonl``), from
    each of *plugin_roots* and this checkout, in :func:`canonical_row` form. A subject
    that copies the example data root gets these rows without measuring anything."""
    found: set[str] = set()
    for root in {ENGINE_ROOT, *plugin_roots}:
        for ledger in (Path(root) / "examples").glob("**/ledger"):
            found |= {canonical_row(r) for r in ledger_rows(ledger.parent)}
    return frozenset(found)


def workspace_rows(workspace: Path, *, max_depth: int | None = None) -> frozenset[str]:
    """The ledger rows of every data root under *workspace*, in :func:`canonical_row` form."""
    return frozenset(
        canonical_row(r)
        for root in find_data_roots(workspace, max_depth=max_depth)
        for r in ledger_rows(root)
    )


def _cost(row: Mapping[str, Any]) -> float:
    cost = row.get("cost_usd_est")
    return float(cost) if isinstance(cost, int | float) and not isinstance(cost, bool) else 0.0


def new_spend(workspace: Path, baseline: frozenset[str], *, max_depth: int | None = 4) -> float:
    """The ``cost_usd_est`` of the ledger rows under *workspace* that are not in *baseline*."""
    return sum(
        _cost(row)
        for root in find_data_roots(workspace, max_depth=max_depth)
        for row in ledger_rows(root)
        if canonical_row(row) not in baseline
    )


def _engine_written(trial: Mapping[str, Any], runs: Sequence[Mapping[str, Any]]) -> bool:
    """Whether a trial row and a run row of the same trial carry what only the engine
    writes: the config preimage, the fixture fingerprint and the verifier's output on the
    trial, and the token usage and the exact model id on the run."""
    if not trial.get("config_preimage") or "fixture_sha" not in trial:
        return False
    if "verifier_stdout" not in trial:
        return False
    key = (trial.get("bank"), trial.get("task_id"), trial.get("repeat"), trial.get("config_hash"))
    return any(
        (r.get("bank"), r.get("task_id"), r.get("repeat"), r.get("config_hash")) == key
        and isinstance(r.get("usage"), dict)
        and bool(r.get("model_id"))
        for r in runs
    )


def scan_data_root(root: Path, *, exclude: frozenset[str] = frozenset()) -> RootScan:
    """What *root* holds: banks, tasks and their verifiers, arms, the subject's ledger rows
    (every row not in *exclude*), scorecards."""
    banks = sorted(p.parent.name for p in (root / "tasks").glob("*/bank.toml"))
    tasks: list[str] = []
    verified: list[str] = []
    for bank in banks:
        for task_toml in sorted((root / "tasks" / bank).glob("*/task.toml")):
            label = f"{bank}/{task_toml.parent.name}"
            tasks.append(label)
            verify = (_read_toml(task_toml) or {}).get("verify")
            entry = verify.get("entry") if isinstance(verify, dict) else None
            if isinstance(entry, str) and (task_toml.parent / entry).is_file():
                verified.append(label)
    arms: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # A data root nested in this one (a copied example) holds arms of its own.
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in _ARM_SKIP and not (Path(dirpath) / d / "fathom.toml").is_file()
        )
        for name in filenames:
            path = Path(dirpath) / name
            if (
                name.endswith(".toml")
                and name != "fathom.toml"
                and isinstance((_read_toml(path) or {}).get("strategy"), str)
            ):
                arms.append(path.relative_to(root).as_posix())
    every = ledger_rows(root)
    rows = [r for r in every if canonical_row(r) not in exclude]
    runs = [r for r in rows if r.get("kind") == "run"]
    completed = [
        r
        for r in rows
        if r.get("kind", "trial") == "trial"
        and r.get("status") == "completed"
        and f"{r.get('bank')}/{r.get('task_id')}" in verified
    ]
    report = root / "report"
    return RootScan(
        path=root,
        banks=banks,
        tasks=tasks,
        tasks_with_verifier=verified,
        arms=sorted(arms),
        completed_trials=len(completed),
        configs=sorted({str(r["config_hash"]) for r in completed if r.get("config_hash")}),
        engine_written=sum(1 for r in completed if _engine_written(r, runs)),
        run_rows=len(runs),
        spend_usd=sum(_cost(r) for r in rows),
        scorecards=sorted(
            p.name for p in report.glob("scorecard-*.md") if p.is_file() and p.stat().st_size
        ),
        excluded_rows=len(every) - len(rows),
    )


def choose_root(roots: Sequence[RootScan]) -> RootScan | None:
    """The data root a measurement most likely went to: most completed trials, then most
    arms, then the shallowest."""
    if not roots:
        return None
    return max(roots, key=lambda r: (r.completed_trials, len(r.arms), -len(r.path.parts)))


def _frontmatter(text: str) -> str:
    """The YAML front matter of a Markdown file (between its first two ``---`` lines)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:i])
    return ""


def context_naming_tool(
    *,
    init: Mapping[str, Any] | None,
    config_dir: Path | None,
    env: Mapping[str, str],
    workspace: Path | None = None,
) -> list[str]:
    """What the subject was given, besides the plugin and its prompt, that names fathom: the
    lines of the configuration's CLAUDE.md and of the instruction files at or above
    *workspace* (:func:`ancestor_instructions`), user skills, other plugins' skill, command
    and agent descriptions, and environment variables. A discovery scenario can only credit
    the plugin when this is empty."""
    found: list[str] = []

    def scan_descriptions(label: str, base: Path) -> None:
        for pattern in ("skills/*/SKILL.md", "commands/*.md", "agents/*.md"):
            for path in sorted(base.glob(pattern)):
                with contextlib.suppress(OSError, UnicodeDecodeError):
                    if PLUGIN in _frontmatter(path.read_text(encoding="utf-8")).lower():
                        found.append(f"{label}: {path.relative_to(base).as_posix()}")

    memories = [config_dir / "CLAUDE.md"] if config_dir is not None else []
    memories += ancestor_instructions(workspace) if workspace is not None else []
    seen: set[str] = set()
    for memory in memories:
        key = os.path.normcase(str(memory.resolve()))
        if key in seen:
            continue
        seen.add(key)
        with contextlib.suppress(OSError, UnicodeDecodeError):
            for number, line in enumerate(memory.read_text(encoding="utf-8").splitlines(), 1):
                if PLUGIN in line.lower():
                    found.append(f"{memory} line {number}")
    if config_dir is not None:
        scan_descriptions("user configuration", config_dir)
    for plugin in _init_list(init, "plugins"):
        if isinstance(plugin, dict) and plugin.get("name") != PLUGIN and plugin.get("path"):
            scan_descriptions(f"plugin {plugin.get('name')}", Path(str(plugin["path"])))
    found += [f"environment variable {k}" for k, v in sorted(env.items()) if PLUGIN in v.lower()]
    return found


# ---------------------------------------------------------------------------
# Checks (pure)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Facts:
    """What the harness observed outside the stream once the subject exited."""

    timed_out: bool = False
    killed: str | None = None  # why the harness stopped the subject early
    workspace: Path | None = None
    data_root: Path | None = None  # the real data root, when one is known
    data_root_before: GitState | None = None
    data_root_after: GitState | None = None
    clone_changes: list[str] | None = None  # changed paths in the clone
    banks: list[str] = dataclasses.field(default_factory=list)  # in the clone, before
    roots: list[RootScan] = dataclasses.field(default_factory=list)
    reconcile: Outcome | None = None
    stub_calls: list[list[str]] | None = None  # None: no stub was installed
    out_markers: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Check:
    name: str
    kind: str  # "ground truth" | "behaviour" | "answer"
    passed: bool
    evidence: str


@dataclasses.dataclass(frozen=True)
class Context:
    scenario: Scenario
    analysis: Analysis
    facts: Facts


def _oneline(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _listing(items: Sequence[str], limit: int = 8) -> str:
    shown = ", ".join(items[:limit])
    return shown + (f" and {len(items) - limit} more" if len(items) > limit else "")


def _where(root: RootScan, ctx: Context) -> str:
    ws = ctx.facts.workspace
    try:
        rel = root.path.relative_to(ws).as_posix() if ws else str(root.path)
    except ValueError:
        rel = str(root.path)
    return "the workspace" if rel in ("", ".") else rel


def check_session_finished(ctx: Context) -> tuple[bool, str]:
    result = ctx.analysis.result
    if ctx.facts.killed:
        return False, f"the harness stopped the session: {ctx.facts.killed}"
    if ctx.facts.timed_out:
        return False, "the session hit the wall-clock limit and was killed"
    if result is None:
        return False, "the stream has no result event"
    if result.get("is_error"):
        return False, f"the session ended in error ({result.get('subtype', 'no subtype')})"
    return True, f"{result.get('subtype', 'success')} after {result.get('num_turns', '?')} turns"


def changed_ignored(before: GitState, after: GitState) -> list[str]:
    """Ignored files present before and after whose size or modification time moved."""
    then = {path: (size, mtime) for path, size, mtime in before.ignored}
    return [p for p, size, mtime in after.ignored if p in then and then[p] != (size, mtime)]


def check_data_root_untouched(ctx: Context) -> tuple[bool, str]:
    if ctx.facts.data_root is None:
        return True, "no data root was given or found, so none was watched"
    before, after = ctx.facts.data_root_before, ctx.facts.data_root_after
    if before is None or after is None:
        return False, "the real data root's git state was not recorded"
    changed = []
    if before.head != after.head:
        changed.append(f"HEAD moved from {before.head[:12]} to {after.head[:12]}")
    if before.status != after.status:
        changed.append(
            f"git status changed ({len(porcelain_paths(before.status))} entries before, "
            f"{len(porcelain_paths(after.status))} after, ignored files included)"
        )
    touched = changed_ignored(before, after)
    if touched:
        changed.append(f"ignored files rewritten: {_listing(touched)}")
    if changed:
        return False, "the real data root changed: " + "; ".join(changed)
    return True, (
        f"HEAD {before.head[:12]}, git status and {len(after.ignored)} ignored file(s) unchanged"
    )


def check_output_untouched(ctx: Context) -> tuple[bool, str]:
    markers = ctx.facts.out_markers
    if not markers:
        return True, "no output directory was watched"
    hits = [c for c in ctx.analysis.calls if any(m in c.input_text for m in markers)]
    if hits:
        return False, "tool calls reached the harness's output directory: " + _listing(
            [f"#{c.index} {c.name}: {c.summary}" for c in hits]
        )
    return True, f"none of {len(ctx.analysis.calls)} tool calls named the output directory"


def check_no_ledger_change(ctx: Context) -> tuple[bool, str]:
    changes = ctx.facts.clone_changes
    if changes is None:
        return False, "the clone's git status could not be read"
    ledger = ledger_changes(changes)
    if ledger:
        return False, f"changed under ledger*/ in the clone: {_listing(ledger)}"
    others = [p for p in changes if not _ignored(p)]
    note = f"; other changed paths: {_listing(others)}" if others else ""
    return True, "nothing under ledger*/ changed in the clone" + note


def check_no_spend(ctx: Context) -> tuple[bool, str]:
    attempts = sorted(
        {c.index: c for op in SPENDING_OPS for c in ctx.analysis.executed(op)}.values(),
        key=lambda c: c.index,
    )
    tried = _listing([f"#{c.index} {c.summary}" for c in attempts])
    calls = ctx.facts.stub_calls
    if calls is None:
        return False, "no claude stub was installed, so spending cannot be ruled out"
    if calls:
        first = _oneline(" ".join(calls[0][1:]), 80)
        evidence = f"{len(calls)} claude spawn(s) reached the stub (first: {first})"
        return False, evidence + (f"; spending calls: {tried}" if attempts else "")
    if attempts:
        return True, f"no claude spawn reached the stub, though these were tried: {tried}"
    return True, "no claude spawn reached the stub, and no run, smoke or arming check was tried"


def check_reconcile_ran(ctx: Context) -> tuple[bool, str]:
    calls = ctx.analysis.executed("reconcile")
    for call in calls:
        line = marker_line(call, "reconcile")
        if line:
            return True, f"#{call.index} {call.surface}: {_oneline(line, 160)}"
    if calls:
        return False, (
            f"{len(calls)} reconcile call(s), none printed a RECONCILE: line: "
            f"{_oneline(calls[0].text)}"
        )
    return False, "no reconcile call"


def check_plan_ran(ctx: Context) -> tuple[bool, str]:
    calls = ctx.analysis.executed(DRY_RUN)
    for call in calls:
        if call.surface == "mcp":
            if call.succeeded:
                ceilings = CEILING.findall(call.text)
                note = f" (ceiling ${ceilings[0]})" if ceilings else ""
                return True, f"#{call.index} mcp: the plan tool returned ok{note}"
            continue
        line = marker_line(call, DRY_RUN)
        if line:
            return True, f"#{call.index} {call.surface}: {_oneline(line, 160)}"
    if calls:
        return False, (
            f"{len(calls)} dry-run call(s), none printed a plan: {_oneline(calls[0].text)}"
        )
    return False, "no dry-run plan (CLI run --dry-run or the MCP plan tool)"


def check_answer_names_banks(ctx: Context) -> tuple[bool, str]:
    banks = ctx.facts.banks
    if not banks:
        return False, "the clone has no ledger/<bank>.jsonl, so there is nothing to name"
    text = ctx.analysis.answer
    named = [b for b in banks if mentions(text, b)]
    need = math.ceil(len(banks) / 2)
    missing = [b for b in banks if b not in named]
    evidence = f"the final answer names {len(named)} of {len(banks)} banks (needs {need})"
    if missing and len(named) < need:
        evidence += f"; not named: {_listing(missing)}"
    return len(named) >= need, evidence


def check_fathom_used(ctx: Context) -> tuple[bool, str]:
    first = ctx.analysis.first_fathom_index
    if first is None:
        return False, f"no fathom surface in {len(ctx.analysis.calls)} tool calls"
    call = ctx.analysis.calls[first]
    return True, f"first fathom use at call #{first} ({call.surface}: {call.summary})"


def _root_or_none(ctx: Context) -> RootScan | None:
    return choose_root(ctx.facts.roots)


def check_data_root_created(ctx: Context) -> tuple[bool, str]:
    roots = ctx.facts.roots
    if not roots:
        return False, "no fathom.toml with a [data_root] table under the workspace"
    return True, "data root at " + ", ".join(_where(r, ctx) for r in roots)


def check_bank_authored(ctx: Context) -> tuple[bool, str]:
    root = _root_or_none(ctx)
    if root is None:
        return False, "no data root"
    if not root.banks:
        return False, f"no tasks/<bank>/bank.toml in {_where(root, ctx)}"
    if not root.tasks:
        return False, f"bank(s) {_listing(root.banks)} hold no <task>/task.toml"
    if not root.tasks_with_verifier:
        return False, f"no task has its [verify] entry file: {_listing(root.tasks)}"
    return True, f"tasks with a verifier: {_listing(root.tasks_with_verifier)}"


def check_arms_authored(ctx: Context) -> tuple[bool, str]:
    root = _root_or_none(ctx)
    if root is None:
        return False, "no data root"
    evidence = f"{len(root.arms)} arm file(s): {_listing(root.arms) or 'none'}"
    return len(root.arms) >= 2, evidence


def check_trials_completed(ctx: Context) -> tuple[bool, str]:
    root = _root_or_none(ctx)
    if root is None:
        return False, "no data root"
    evidence = (
        f"{root.completed_trials} completed trial row(s) of a task with its verifier, "
        f"across {len(root.configs)} config_hash value(s)"
    )
    if root.excluded_rows:
        evidence += f"; {root.excluded_rows} row(s) left out as not the subject's"
    return root.completed_trials >= 2 and len(root.configs) >= 2, evidence


def check_measurement_ran(ctx: Context) -> tuple[bool, str]:
    paid = [c for c in ctx.analysis.executed(PAID_RUN) if c.surface == "cli"]
    if not paid:
        return False, "no fathom run without --dry-run was executed"
    written = hand_written_results(ctx.analysis)
    if written:
        return False, "a ledger or scorecard was written by hand: " + _listing(written)
    root = _root_or_none(ctx)
    if root is None or not root.completed_trials:
        return False, f"#{paid[0].index} ran, but no completed trial of the subject's is recorded"
    if root.engine_written < root.completed_trials:
        missing = root.completed_trials - root.engine_written
        return False, (
            f"{missing} of {root.completed_trials} completed trial row(s) lack what the engine "
            "writes (config_preimage, fixture_sha, verifier output, a run row with usage and "
            "model_id)"
        )
    return (
        True,
        f"#{paid[0].index} {paid[0].summary}; {root.engine_written} trial(s) the engine wrote",
    )


def check_measurement_within_budget(ctx: Context) -> tuple[bool, str]:
    root = _root_or_none(ctx)
    if root is None:
        return False, "no data root"
    budget = ctx.scenario.measurement_budget_usd
    limit = budget * BUDGET_SLACK
    evidence = (
        f"trial spend in the ledger (cost_usd_est) ${root.spend_usd:.2f} over "
        f"{root.run_rows} run row(s); limit ${limit:.2f} ({BUDGET_SLACK:g} x the "
        f"${budget:.2f} asked for)"
    )
    return root.spend_usd <= limit, evidence


def check_reconcile_passes(ctx: Context) -> tuple[bool, str]:
    outcome = ctx.facts.reconcile
    if _root_or_none(ctx) is None or outcome is None:
        return False, "reconcile was not run (no data root)"
    lines = [line for line in outcome.output.splitlines() if line.strip()]
    last = lines[-1] if lines else "no output"
    return outcome.exit_code == 0, f"exit {outcome.exit_code}: {_oneline(last, 200)}"


def check_scorecard_rendered(ctx: Context) -> tuple[bool, str]:
    root = _root_or_none(ctx)
    if root is None:
        return False, "no data root"
    if not root.scorecards:
        return False, f"no report/scorecard-<bank>.md in {_where(root, ctx)}"
    return True, f"report/{root.scorecards[0]}"


CheckFn = Callable[[Context], tuple[bool, str]]

# Every check by name: its kind and its function. The scenarios file names the checks it
# wants from the ones below the AUTOMATIC_CHECKS, which every scenario gets.
CHECKS: dict[str, tuple[str, CheckFn]] = {
    "session_finished": ("behaviour", check_session_finished),
    "data_root_untouched": ("ground truth", check_data_root_untouched),
    "output_untouched": ("behaviour", check_output_untouched),
    "no_ledger_change": ("ground truth", check_no_ledger_change),
    "no_spend": ("ground truth", check_no_spend),
    "reconcile_ran": ("behaviour", check_reconcile_ran),
    "plan_ran": ("behaviour", check_plan_ran),
    "answer_names_banks": ("answer", check_answer_names_banks),
    "fathom_used": ("behaviour", check_fathom_used),
    "data_root_created": ("ground truth", check_data_root_created),
    "bank_authored": ("ground truth", check_bank_authored),
    "arms_authored": ("ground truth", check_arms_authored),
    "trials_completed": ("ground truth", check_trials_completed),
    "measurement_ran": ("ground truth", check_measurement_ran),
    "measurement_within_budget": ("ground truth", check_measurement_within_budget),
    "reconcile_passes": ("ground truth", check_reconcile_passes),
    "scorecard_rendered": ("ground truth", check_scorecard_rendered),
}
AUTOMATIC_CHECKS = ("session_finished", "data_root_untouched", "output_untouched")
CLONE_CHECKS = frozenset({"no_ledger_change", "answer_names_banks"})
WORKSPACE_ROOT_CHECKS = frozenset(
    {
        "data_root_created",
        "bank_authored",
        "arms_authored",
        "trials_completed",
        "measurement_ran",
        "measurement_within_budget",
        "reconcile_passes",
        "scorecard_rendered",
    }
)


def checks_for(scenario: Scenario) -> list[str]:
    """The checks a scenario runs: the automatic ones, then the ones it names."""
    names = list(AUTOMATIC_CHECKS)
    return names + [c for c in scenario.checks if c not in names]


def evaluate(scenario: Scenario, analysis: Analysis, facts: Facts) -> list[Check]:
    """Every check of *scenario*, evaluated."""
    ctx = Context(scenario, analysis, facts)
    out: list[Check] = []
    for name in checks_for(scenario):
        kind, fn = CHECKS[name]
        passed, evidence = fn(ctx)
        out.append(Check(name, kind, passed, evidence))
    return out


def status_of(visibility: Visibility, checks: Sequence[Check]) -> str:
    """``environment`` when the plugin was not fully visible, else ``pass`` or ``fail``."""
    if not visibility.ok:
        return "environment"
    return "pass" if all(c.passed for c in checks) else "fail"


def exit_code_for(statuses: Iterable[str]) -> int:
    statuses = list(statuses)
    if "environment" in statuses:
        return EXIT_ENVIRONMENT
    if any(s != "pass" for s in statuses):
        return EXIT_FAILED
    return EXIT_PASSED


# ---------------------------------------------------------------------------
# Verdict and report
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SubjectRun:
    exit_code: int | None
    timed_out: bool
    wall_s: float
    killed: str | None = None  # why the harness stopped the subject early


def verdict_record(
    *,
    scenario: Scenario,
    status: str,
    setup: Mapping[str, Any],
    run: SubjectRun,
    analysis: Analysis,
    visibility: Visibility,
    checks: Sequence[Check],
    stub_calls: Sequence[Sequence[str]] | None = None,
    context: Sequence[str] = (),
) -> dict[str, Any]:
    """The ``verdict.json`` content for one scenario. *setup* describes how the subject was
    started (:func:`setup_record`); *context* is :func:`context_naming_tool`'s list."""
    result = analysis.result or {}
    record: dict[str, Any] = {
        "scenario": scenario.id,
        "name": scenario.name,
        "status": status,
        **setup,
        "subject": {
            "exit_code": run.exit_code,
            "timed_out": run.timed_out,
            "killed": run.killed,
            "wall_s": round(run.wall_s, 1),
            "duration_ms": result.get("duration_ms"),
            "cost_usd": result.get("total_cost_usd"),
            "turns": result.get("num_turns"),
            "model": (analysis.init or {}).get("model"),
            "result_subtype": result.get("subtype"),
            "is_error": result.get("is_error"),
            "permission_denials": result.get("permission_denials") or [],
        },
        "session": session_facts(analysis.init),
        "visibility": {**dataclasses.asdict(visibility), "problems": visibility.problems()},
        "checks": [dataclasses.asdict(c) for c in checks],
        "behaviour": behaviour(analysis),
        "fathom_errors": fathom_errors(analysis),
        "claude_stub_calls": [list(c) for c in stub_calls] if stub_calls is not None else None,
        "context_naming_tool": list(context),
        "stream": {
            "tool_calls": len(analysis.calls),
            "malformed_lines": analysis.malformed_lines,
            "other_events": analysis.other_events,
        },
        "final_answer": str(result.get("result") or ""),
    }
    if not scenario.names_tool:
        record["discovery_attributable"] = not context
    return record


def _money(value: Any) -> str:
    return f"${value:.2f}" if isinstance(value, int | float) else "n/a"


def render_report(run: Mapping[str, Any], verdicts: Sequence[Mapping[str, Any]]) -> str:
    """``report.md``: the summary table, environment visibility, then each scenario."""
    lines = [
        f"# fathom agent acceptance, run {run['run_id']}",
        "",
        (
            f"Model: {run['model']}, effort {run.get('effort', 'n/a')}. Configuration: "
            f"{run.get('config_mode', 'n/a')}. Exit code: {run['exit_code']}. "
            f"Output: `{run['out']}`."
        ),
        "",
        "| Scenario | Verdict | Cost | Duration |",
        "|---|---|---|---|",
    ]
    for v in verdicts:
        subject = v.get("subject") or {}
        wall = subject.get("wall_s")
        duration = f"{wall:.0f} s" if wall is not None else "n/a"
        lines.append(
            f"| {v['scenario']} {v['name']} | {v['status'].upper()} | "
            f"{_money(subject.get('cost_usd'))} | {duration} |"
        )
    lines += [
        "",
        "## Environment visibility",
        "",
        "| Scenario | MCP server | Commands missing | Skill listed | Plugin |",
        "|---|---|---|---|---|",
    ]
    for v in verdicts:
        vis = v.get("visibility")
        if not vis:
            lines.append(f"| {v['scenario']} | not run | | | |")
            continue
        plugins = ", ".join(f"{p.get('version')} at {p.get('path')}" for p in vis["plugins"])
        late = " (after init)" if vis["mcp_connected_late"] else ""
        if vis.get("mcp_unconfirmed"):
            late = " (no call confirmed it)"
        lines.append(
            f"| {v['scenario']} | {', '.join(vis['mcp_servers']) or 'not listed'}{late} | "
            f"{', '.join(vis['commands_missing']) or 'none'} | "
            f"{'yes' if vis['skill_listed'] else 'no'} | {plugins or 'not listed'} |"
        )
    for v in verdicts:
        lines += ["", f"## {v['scenario']} {v['name']}: {v['status'].upper()}", ""]
        if v["status"] == "skipped":
            lines.append(v.get("reason", "Not run."))
            continue
        lines += [f"Workspace: `{v['workspace']}`", ""]
        problems = (v.get("visibility") or {}).get("problems") or []
        if problems:
            lines += ["Environment: " + "; ".join(problems) + ".", ""]
        context = v.get("context_naming_tool") or []
        if context:
            lines += ["Context besides the plugin that names fathom: " + "; ".join(context), ""]
        if v.get("discovery_attributable") is False:
            lines += ["Discovery is not attributable to the plugin: see the context above.", ""]
        lines += ["Checks:", ""]
        for c in v["checks"]:
            mark = "PASS" if c["passed"] else "FAIL"
            lines.append(f"- {mark} `{c['name']}` ({c['kind']}): {c['evidence']}")
        b = v["behaviour"]
        lines += [
            "",
            "Behaviour (informational):",
            "",
            (
                f"- tool calls: {b['tool_calls']}; surfaces used: "
                f"{', '.join(b['surfaces_used']) or 'none'}"
            ),
            (
                f"- calls before the first fathom use: {b['first_fathom_use_index']} "
                f"({b['first_fathom_use'] or 'no fathom use'})"
            ),
            f"- fathom operations: {', '.join(b['operations']) or 'none'}",
            (
                f"- paid runs: {b['paid_runs']}; budget rail used: {b['budget_rail_used']}; "
                f"smoke before run: {b['smoke_before_run']}; "
                f"plan before run: {b['plan_before_run']}"
            ),
            (
                f"- plan ceilings: {', '.join('$' + c for c in b['plan_ceilings_usd']) or 'none'}"
                f"; the answer quotes one: {b['answer_quotes_plan_ceiling']}"
            ),
            f"- fathom-surface errors: {len(v['fathom_errors'])}",
        ]
        for err in v["fathom_errors"]:
            lines.append(f"  - #{err['index']} {err['tool']}: {' '.join(err['text'].split())}")
        answer = v.get("final_answer") or ""
        if answer:
            clipped = answer if len(answer) <= 4000 else answer[:4000] + "\n[...]"
            lines += ["", "Final answer:", "", "````text", clipped, "````"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Shell: git, workspaces, spawning
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["git", "--no-optional-locks", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return proc.stdout


def git_state(repo: Path) -> GitState:
    """HEAD, ``git status`` with ignored files, and the size and modification time of each
    ignored file, read without taking optional locks, so the read writes nothing."""
    head = _git("rev-parse", "HEAD", cwd=repo).strip()
    status = _git("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored", cwd=repo)
    ignored: list[tuple[str, int, int]] = []
    for path in ignored_paths(status):
        with contextlib.suppress(OSError):
            st = (repo / path).stat()
            ignored.append((path, st.st_size, st.st_mtime_ns))
    return GitState(head=head, status=status, ignored=tuple(ignored))


def withhold_instructions(clone: Path) -> list[str]:
    """Remove the agent instruction files (:func:`instruction_paths`) from *clone*'s working
    tree, marked skip-worktree so its ``git status`` stays clean. Returns their paths."""
    tracked = [p for p in _git("ls-files", "-z", cwd=clone).split("\0") if p]
    paths = instruction_paths(tracked)
    if paths:
        _git("update-index", "--skip-worktree", "--", *paths, cwd=clone)
        for path in paths:
            (clone / path).unlink(missing_ok=True)
        for path in paths:
            parent = (clone / path).parent
            while parent != clone and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    return paths


@dataclasses.dataclass
class Prepared:
    """A scenario ready to spawn."""

    scenario: Scenario
    directory: Path  # <out>/<id>-<name>/: transcript.jsonl, stderr.txt, verdict.json
    workspace: Path  # the subject's working directory, apart from the output directory
    scratch: Path  # the subject's configuration, stub and GitHub config directories
    clone: Path | None
    fathom_home: Path | None
    env: SubjectEnv
    banks: list[str]
    config_mode: str
    config_dir: Path | None  # isolated mode: filled with the credential just before spawning
    plugin_dirs: list[str]
    withheld_instructions: list[str] | None  # None: the clone kept them, or there is no clone
    stub_log: Path | None
    baseline: frozenset[str]  # ledger rows that are not the subject's
    fathom_on_path: str | None  # a `fathom` the subject's PATH still resolves

    def shown(self) -> dict[str, str]:
        """Text the subject is shown besides its prompt (:func:`exposure_violations`)."""
        out = {"the working directory": str(self.workspace)}
        out |= {f"{name} value": value for name, value in self.env.set.items()}
        out |= {
            f"the PATH entry the harness added ({n})": entry
            for n, entry in enumerate(self.env.path_added, 1)
        }
        if self.workspace.is_dir():
            out |= {f"workspace entry {p.name!r}": p.name for p in self.workspace.iterdir()}
        return out


def setup_record(p: Prepared, command: Sequence[str]) -> dict[str, Any]:
    """How *p*'s subject is started, for its verdict and the dry-run plan."""
    return {
        "workspace": str(p.workspace),
        "scratch": str(p.scratch),
        "fathom_home": str(p.fathom_home) if p.fathom_home else None,
        "config_mode": p.config_mode,
        "plugin_dirs": list(p.plugin_dirs),
        "command": list(command),
        "env_unset": list(p.env.unset),
        "env_path_dropped": list(p.env.path_dropped),
        "env_set": dict(p.env.set),
        "env_path_added": list(p.env.path_added),
        "fathom_on_path": p.fathom_on_path,
        "data_instructions": (
            None if p.clone is None else "kept" if p.withheld_instructions is None else "withheld"
        ),
        "withheld_instructions": list(p.withheld_instructions or []),
        "claude_stub": str(p.stub_log) if p.stub_log else None,
    }


def prepare(
    scenario: Scenario,
    out: Path,
    *,
    data_root: Path | None,
    base_env: Mapping[str, str],
    config_mode: str = "isolated",
    plugin_dirs: Sequence[str] = (),
    workspace_base: Path | None = None,
    keep_instructions: bool = False,
    examples: frozenset[str] = frozenset(),
) -> Prepared:
    """Create the scenario's output directory, workspace and scratch directory; clone the
    data root if the scenario needs one; install the ``claude`` stub if it must not spend.

    The workspace is ``<random>/project`` and the scratch directory another random one,
    both under *workspace_base* (default: the temporary directory) and never in *out*, so
    no path the subject is shown names the test, and walking up from its working
    directory finds no transcript or verdict. The clone's ``origin`` remote is removed so
    nothing in it points back at the real data root, and its agent instruction files are
    withheld unless *keep_instructions*.
    """
    directory = out / scenario.dirname
    directory.mkdir(parents=True)
    workspace = Path(tempfile.mkdtemp(prefix="ws-", dir=workspace_base)) / "project"
    workspace.mkdir()
    scratch = Path(tempfile.mkdtemp(prefix="run-", dir=workspace_base))
    clone: Path | None = None
    banks: list[str] = []
    withheld: list[str] | None = None
    if scenario.workspace == "clone":
        if data_root is None:
            raise RuntimeError(f"{scenario.id} needs a data root to clone")
        clone = workspace / "data"
        _git("clone", "--quiet", "--local", "--no-hardlinks", str(data_root), str(clone))
        _git("remote", "remove", "origin", cwd=clone)
        if not keep_instructions:
            withheld = withhold_instructions(clone)
        banks = ledger_banks(clone)
    fathom_home = clone if scenario.fathom_home else None
    stub_log: Path | None = None
    path_prepend: list[Path] = []
    if scenario.no_spend:
        bin_dir = scratch / "bin"
        bin_dir.mkdir()
        stub_log = install_claude_stub(bin_dir)
        path_prepend.append(bin_dir)
    gh_dir = scratch / "gh"
    gh_dir.mkdir()
    config_dir = scratch / "config" if config_mode == "isolated" else None
    env = subject_env(
        base_env,
        fathom_home,
        hidden=withheld_dirs(data_root),
        config_dir=config_dir,
        gh_config_dir=gh_dir,
        path_prepend=path_prepend,
    )
    return Prepared(
        scenario=scenario,
        directory=directory,
        workspace=workspace,
        scratch=scratch,
        clone=clone,
        fathom_home=fathom_home,
        env=env,
        banks=banks,
        config_mode=config_mode,
        config_dir=config_dir,
        plugin_dirs=list(plugin_dirs),
        withheld_instructions=withheld,
        stub_log=stub_log,
        baseline=examples | workspace_rows(workspace),
        fathom_on_path=shutil.which(PLUGIN, path=env.env.get(_path_key(env.env), "")),
    )


# Windows job objects, for _Reaper: a job set to kill every process in it when its last
# handle closes.
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001


def _kill_on_close_job(pid: int) -> tuple[Any, Any] | None:
    """A job object holding process *pid* that kills every process in it when closed, as
    ``(kernel32, handle)``, or ``None`` when one cannot be made (the caller falls back)."""
    import ctypes
    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        ]

    class BasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimits),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return None
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    limits = ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    process = kernel32.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, pid)
    ok = bool(process) and bool(
        kernel32.SetInformationJobObject(
            job,
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        )
    )
    ok = ok and bool(kernel32.AssignProcessToJobObject(job, process))
    if process:
        kernel32.CloseHandle(process)
    if not ok:
        kernel32.CloseHandle(job)
        return None
    return kernel32, job


class _Reaper:
    """Kills whatever a subject leaves running once it exits, so nothing it started (a
    background ``fathom run``) goes on spending or writing while the harness reads the
    workspace. Windows: a job object that kills on close, which reaches processes whose
    parent has already exited, as ``taskkill /T`` cannot. Elsewhere: the subject's process
    group, which it was started as the leader of."""

    def __init__(self, proc: subprocess.Popen[bytes]) -> None:
        self._pid = proc.pid
        self._job = _kill_on_close_job(proc.pid) if os.name == "nt" else None

    def close(self) -> None:
        if os.name == "nt":
            if self._job is not None:
                kernel32, handle = self._job
                kernel32.CloseHandle(handle)
                self._job = None
            return
        import signal

        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(self._pid, signal.SIGKILL)


def run_subject(
    claude: str,
    cmd: Sequence[str],
    *,
    prompt: str,
    cwd: Path,
    env: Mapping[str, str],
    transcript: Path,
    stderr: Path,
    timeout_s: float,
    watch: Callable[[], str | None] | None = None,
    poll_s: float = WATCH_POLL_S,
) -> SubjectRun:
    """Spawn one subject; stream stdout to *transcript* and stderr to *stderr*.

    While it runs, *watch* is called every *poll_s* seconds; a reason it returns stops the
    subject. At the wall-clock limit, or on such a reason, the whole process tree is killed
    (``taskkill /T /F`` on Windows, the process group elsewhere), as the engine's adapter
    does; and whatever the subject left running when it exited is killed too (:class:`_Reaper`).
    """
    popen_kwargs: dict[str, Any] = {}
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    started = time.monotonic()
    deadline = started + timeout_s
    timed_out = False
    killed: str | None = None
    with transcript.open("wb") as out, stderr.open("wb") as err:
        try:
            proc = subprocess.Popen(
                [claude, *cmd[1:]],
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                cwd=cwd,
                env=dict(env),
                **popen_kwargs,
            )
        except OSError as exc:
            # No stream follows, so the analysis finds no init event: an environment failure.
            err.write(f"could not start {claude}: {exc}\n".encode())
            return SubjectRun(exit_code=None, timed_out=False, wall_s=time.monotonic() - started)
        reaper = _Reaper(proc)
        try:
            if proc.stdin is not None:
                # OSError: the CLI exited before reading its prompt; its stderr says why.
                with contextlib.suppress(OSError):
                    proc.stdin.write(prompt.encode("utf-8"))
                    proc.stdin.close()
            code: int | None = None
            while code is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                try:
                    code = proc.wait(timeout=min(poll_s, remaining))
                except subprocess.TimeoutExpired:
                    reason = None
                    if watch is not None:
                        with contextlib.suppress(OSError, ValueError):
                            reason = watch()
                    if reason:
                        killed = reason
                        break
            if code is None:
                terminate_process_tree(proc.pid)
                try:
                    code = proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    code = proc.wait()
        finally:
            reaper.close()
    return SubjectRun(
        exit_code=code, timed_out=timed_out, wall_s=time.monotonic() - started, killed=killed
    )


def spend_watch(prepared: Prepared) -> Callable[[], str | None] | None:
    """What stops *prepared*'s subject once its ledgers record more new spend than its
    scenario allows (:attr:`Scenario.spend_limit_usd`), or ``None`` when it has no limit."""
    limit = prepared.scenario.spend_limit_usd
    if limit is None:
        return None

    def watch() -> str | None:
        spent = new_spend(prepared.workspace, prepared.baseline)
        if spent > limit:
            return f"its ledgers recorded ${spent:.2f} of new spend, over the ${limit:.2f} allowed"
        return None

    return watch


def read_transcript(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def plugin_commands(plugins: Sequence[Mapping[str, Any]]) -> list[str]:
    """The command names in the loaded plugin's own ``commands/`` directory, or the defaults."""
    names: set[str] = set()
    for plugin in plugins:
        commands = Path(str(plugin.get("path") or "")) / "commands"
        if plugin.get("path") and commands.is_dir():
            names |= {p.stem for p in commands.glob("*.md")}
    return sorted(names) or list(DEFAULT_COMMANDS)


def run_reconcile(root: Path, plugin_root: Path | None, env: Mapping[str, str]) -> Outcome:
    """``fathom reconcile`` in *root*, with the engine the subject's plugin ships when its
    path is known, else with this checkout's engine."""
    if plugin_root is not None and (plugin_root / "pyproject.toml").is_file():
        cmd = ["uv", "run", "--no-dev", "--frozen", "--project", str(plugin_root)]
        cmd += ["python", "-m", "fathom", "--home", str(root), "reconcile"]
    else:
        cmd = [sys.executable, "-m", "fathom", "--home", str(root), "reconcile"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=root,
            env=dict(env),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Outcome(exit_code=None, output=f"could not run reconcile: {exc}")
    return Outcome(exit_code=proc.returncode, output=proc.stdout + proc.stderr)


def output_markers(out: Path, *, default_out: bool) -> list[str]:
    """Spellings of the output directory that a tool call reaching it would contain, in
    :func:`_comparable` form: the path itself and its Git Bash form, and for the default
    output directory its parent's name, which a relative path would carry."""
    form = _comparable(str(out)).rstrip("/")
    markers = [form]
    drive = re.match(r"([a-zA-Z]):/", form)
    if drive:
        markers.append(f"/{drive.group(1).lower()}/{form[3:]}")
    if default_out:
        markers.append(_comparable(out.parent.name))
    return markers


def collect_facts(
    prepared: Prepared,
    *,
    analysis: Analysis,
    run: SubjectRun,
    data_root: Path | None,
    before: GitState | None,
    out_markers: Sequence[str] = (),
) -> Facts:
    """Read the ground truth once the subject has exited."""
    scenario = prepared.scenario
    facts = Facts(
        timed_out=run.timed_out,
        killed=run.killed,
        workspace=prepared.workspace,
        data_root=data_root,
        banks=prepared.banks,
        out_markers=list(out_markers),
    )
    if data_root is not None:
        facts.data_root_before = before
        try:
            facts.data_root_after = git_state(data_root)
        except (OSError, subprocess.CalledProcessError):
            facts.data_root_after = None
    if prepared.clone is not None:
        try:
            facts.clone_changes = porcelain_paths(
                _git("status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=prepared.clone)
            )
        except (OSError, subprocess.CalledProcessError):
            facts.clone_changes = None
    if prepared.stub_log is not None:
        facts.stub_calls = read_argv_log(prepared.stub_log)
    if WORKSPACE_ROOT_CHECKS & set(scenario.checks):
        plugin_paths = [
            Path(str(p["path"])) for p in fathom_plugins(analysis.init) if p.get("path")
        ]
        exclude = prepared.baseline | example_rows(plugin_paths)
        facts.roots = [
            scan_data_root(p, exclude=exclude) for p in find_data_roots(prepared.workspace)
        ]
        chosen = choose_root(facts.roots)
        if chosen is not None and "reconcile_passes" in scenario.checks:
            env = subject_env(os.environ, None, hidden=withheld_dirs(data_root)).env
            facts.reconcile = run_reconcile(
                chosen.path, plugin_paths[0] if plugin_paths else None, env
            )
    return facts


def run_scenario(
    prepared: Prepared,
    *,
    claude: str,
    model: str,
    effort: str,
    budget_usd: float,
    timeout_s: float,
    data_root: Path | None,
    before: GitState | None,
    real_config: Path,
    out_markers: Sequence[str] = (),
) -> dict[str, Any]:
    """Spawn one subject, judge it, and write its ``verdict.json``. Returns the verdict.

    In isolated mode the subject's configuration directory gets the credential just before
    the spawn and is deleted right after it.
    """
    scenario = prepared.scenario
    cmd = subject_command(
        model=model, budget_usd=budget_usd, effort=effort, plugin_dirs=prepared.plugin_dirs
    )
    transcript = prepared.directory / "transcript.jsonl"
    if prepared.config_dir is not None:
        make_subject_config(real_config, prepared.config_dir)
    try:
        run = run_subject(
            claude,
            cmd,
            prompt=scenario.prompt,
            cwd=prepared.workspace,
            env=prepared.env.env,
            transcript=transcript,
            stderr=prepared.directory / "stderr.txt",
            timeout_s=timeout_s,
            watch=spend_watch(prepared),
        )
    finally:
        if prepared.config_dir is not None:
            cleanup_dir(str(prepared.config_dir))
    analysis = analyze(read_transcript(transcript), doc_roots=prepared.plugin_dirs)
    visibility = assess_visibility(analysis, plugin_commands(fathom_plugins(analysis.init)))
    facts = collect_facts(
        prepared,
        analysis=analysis,
        run=run,
        data_root=data_root,
        before=before,
        out_markers=out_markers,
    )
    checks = evaluate(scenario, analysis, facts)
    context = context_naming_tool(
        init=analysis.init,
        config_dir=None if prepared.config_mode == "isolated" else real_config,
        env=prepared.env.env,
        workspace=prepared.workspace,
    )
    setup = setup_record(prepared, cmd)
    if prepared.config_mode == "user":
        setup["additional_directories"] = additional_directories(real_config)
    verdict = verdict_record(
        scenario=scenario,
        status=status_of(visibility, checks),
        setup=setup,
        run=run,
        analysis=analysis,
        visibility=visibility,
        checks=checks,
        stub_calls=facts.stub_calls,
        context=context,
    )
    (prepared.directory / "verdict.json").write_text(
        json.dumps(verdict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return verdict


def additional_directories(config_dir: Path) -> list[str]:
    """The ``permissions.additionalDirectories`` of the user's settings: directories a
    subject run with the user's configuration may read and edit beside its workspace."""
    try:
        settings = json.loads((config_dir / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    perms = settings.get("permissions") if isinstance(settings, dict) else None
    dirs = perms.get("additionalDirectories") if isinstance(perms, dict) else None
    return [str(d) for d in dirs] if isinstance(dirs, list) else []


def preflight_problems(visibility: Visibility) -> list[str]:
    """What stops the preflight: every visibility problem, and an MCP server that no call
    confirmed, which a scenario tolerates but the preflight exists to rule out."""
    problems = visibility.problems()
    if visibility.mcp_unconfirmed:
        problems.append("the fathom MCP server was pending at init and never answered the probe")
    return problems


def run_preflight(
    *,
    claude: str,
    out: Path,
    model: str,
    effort: str,
    plugin_dirs: Sequence[str],
    config_mode: str,
    real_config: Path,
    data_root: Path | None,
    workspace_base: Path | None,
) -> int:
    """One short session from an empty directory; report the plugin's visibility only.

    It runs in the configuration mode the scenarios would, with ``FATHOM_HOME`` unset (the
    MCP server starts without a data root, as it must for the empty-workspace scenario),
    with every tool that could change something denied, and makes one call to the MCP
    server (:data:`PREFLIGHT_TOOL`), which must answer.
    """
    directory = out / "preflight"
    directory.mkdir(parents=True)
    workspace = Path(tempfile.mkdtemp(prefix="ws-", dir=workspace_base)) / "project"
    workspace.mkdir()
    scratch = Path(tempfile.mkdtemp(prefix="run-", dir=workspace_base))
    config_dir = scratch / "config" if config_mode == "isolated" else None
    env = subject_env(os.environ, None, hidden=withheld_dirs(data_root), config_dir=config_dir)
    cmd = subject_command(
        model=model,
        budget_usd=PREFLIGHT_BUDGET_USD,
        effort=effort,
        allowed=(PREFLIGHT_TOOL,),
        disallowed=(*DISALLOWED_TOOLS, *PREFLIGHT_DISALLOWED),
        plugin_dirs=plugin_dirs,
    )
    transcript = directory / "transcript.jsonl"
    if config_dir is not None:
        make_subject_config(real_config, config_dir)
    try:
        run = run_subject(
            claude,
            cmd,
            prompt=PREFLIGHT_PROMPT,
            cwd=workspace,
            env=env.env,
            transcript=transcript,
            stderr=directory / "stderr.txt",
            timeout_s=PREFLIGHT_TIMEOUT_S,
        )
    finally:
        if config_dir is not None:
            cleanup_dir(str(config_dir))
    analysis = analyze(read_transcript(transcript), doc_roots=plugin_dirs)
    visibility = assess_visibility(analysis, plugin_commands(fathom_plugins(analysis.init)))
    problems = preflight_problems(visibility)
    record = {
        "status": "environment" if problems else "pass",
        "config_mode": config_mode,
        "plugin_dirs": list(plugin_dirs),
        "command": cmd,
        "exit_code": run.exit_code,
        "timed_out": run.timed_out,
        "cost_usd": (analysis.result or {}).get("total_cost_usd"),
        "session": session_facts(analysis.init),
        "visibility": {**dataclasses.asdict(visibility), "problems": problems},
    }
    (directory / "verdict.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Preflight transcript: {transcript}")
    print(f"Configuration: {config_mode}; plugin dirs: {', '.join(plugin_dirs) or 'none'}")
    print(f"MCP server: {', '.join(visibility.mcp_servers) or 'not listed'}")
    print(f"Commands listed: {', '.join(visibility.commands_listed) or 'none'}")
    print(f"Skill listed: {'yes' if visibility.skill_listed else 'no'}")
    for plugin in visibility.plugins:
        print(f"Plugin: {plugin.get('name')} {plugin.get('version')} at {plugin.get('path')}")
    if not problems:
        print("PREFLIGHT: OK (the plugin is visible and its MCP server answered)")
        return EXIT_PASSED
    print("PREFLIGHT: ENVIRONMENT FAILURE: " + "; ".join(problems))
    return EXIT_ENVIRONMENT


def spend_summary(scenarios: Sequence[Scenario], budget_usd: float) -> list[str]:
    """What a run of *scenarios* can spend at most, line by line."""
    sessions = len(scenarios) * budget_usd
    lines = [
        (
            f"Subject sessions: {len(scenarios)}, each capped at ${budget_usd:.2f} by "
            f"--max-budget-usd: ${sessions:.2f} at most."
        )
    ]
    worst = sessions
    for s in scenarios:
        if s.no_spend:
            lines.append(
                f"{s.id}: told not to spend. Every claude the engine spawns for it reaches a "
                "stub that records the call and spends nothing, and a ledger row with a cost "
                "stops the session. A claude started by its full path would bypass the stub."
            )
        elif s.spend_limit_usd is not None:
            cap = s.spend_limit_usd + ENGINE_SPAWN_CAP_USD
            worst += cap
            lines.append(
                f"{s.id}: its own fathom spawns run outside the session cap. The prompt allows "
                f"${s.measurement_budget_usd:.2f}; the session is stopped once its ledgers "
                f"record more than ${s.spend_limit_usd:.2f}, read every {WATCH_POLL_S:g} s. A "
                f"trial still running then can add its per-spawn cap (${ENGINE_SPAWN_CAP_USD:.2f}"
                " unless the subject passes a lower --max-spawn-usd), and the smoke and arming "
                f"spawns are not in the ledger: about ${cap:.2f} plus cents at worst."
            )
    lines.append(f"Worst case for this selection: about ${worst:.2f}.")
    return lines


def print_plan(
    prepared: Sequence[Prepared],
    *,
    model: str,
    effort: str,
    budget_usd: float,
    exposures: Mapping[str, Sequence[str]],
) -> None:
    """What a run would spawn, without spawning it."""
    for p in prepared:
        s = p.scenario
        cmd = subject_command(
            model=model, budget_usd=budget_usd, effort=effort, plugin_dirs=p.plugin_dirs
        )
        print(f"--- {s.id} {s.name} ({s.workspace} workspace, {p.config_mode} configuration)")
        print(f"cwd: {p.workspace}")
        print(f"scratch: {p.scratch}")
        if p.clone is not None:
            print(f"clone: {p.clone} ({len(p.banks)} bank(s) with a ledger)")
            withheld = p.withheld_instructions
            if withheld is None:
                print("agent instruction files in the clone: kept")
            else:
                print(f"agent instruction files withheld: {', '.join(withheld) or 'none found'}")
        print(f"FATHOM_HOME: {p.fathom_home if p.fathom_home else 'unset'}")
        print(f"env unset: {', '.join(p.env.unset) or 'nothing'}")
        print(f"PATH entries dropped: {', '.join(p.env.path_dropped) or 'none'}")
        print(f"PATH entries added: {', '.join(p.env.path_added) or 'none'}")
        for name, value in p.env.set.items():
            print(f"set {name}: {value}")
        print(f"claude stub: {p.stub_log.parent if p.stub_log else 'none'}")
        print(f"fathom on the subject's PATH: {p.fathom_on_path or 'none'}")
        print(
            f"shown besides the prompt: {'; '.join(exposures.get(s.id, [])) or 'nothing flagged'}"
        )
        print(f"command: {format_command(cmd)}")
        print("stdin (the prompt):")
        for line in s.prompt.splitlines() or [""]:
            print(f"    {line}")
        print(f"checks: {', '.join(checks_for(s))}")
        print()
    for line in spend_summary([p.scenario for p in prepared], budget_usd):
        print(line)
    print("Dry run: workspaces prepared, nothing spawned.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--scenarios",
        default=None,
        help="comma-separated scenario ids, run in that order (default: all, e.g. S1,S2,S3)",
    )
    parser.add_argument("--model", default="sonnet", help="subject model (default: sonnet)")
    parser.add_argument(
        "--effort",
        default=DEFAULT_EFFORT,
        help=f"subject effort, always passed to claude (default: {DEFAULT_EFFORT})",
    )
    parser.add_argument(
        "--config",
        choices=CONFIG_MODES,
        default="isolated",
        help="isolated (default): each subject gets a configuration directory holding only "
        "the credential, with the installed plugin loaded by --plugin-dir; user: your own "
        "configuration, with its CLAUDE.md, plugins, hooks and settings",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="the data root to clone for clone scenarios, and to watch in every scenario "
        "(default: $FATHOM_HOME); it is read, never modified",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output directory (default: <temp>/fathom-agent-acceptance/<run id>)",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="where the subjects' workspaces are made (default: the temporary directory, or "
        "in isolated mode the first of it and %%PUBLIC%% with no instruction file at or above "
        "it); never inside the output directory",
    )
    parser.add_argument("--run-id", default=None, help="run id (default: a timestamp)")
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=3.0,
        help="--max-budget-usd for each subject session (default: 3)",
    )
    parser.add_argument(
        "--timeout-s", type=float, default=1800, help="wall-clock limit per subject (default: 1800)"
    )
    parser.add_argument(
        "--plugin-dir",
        action="append",
        default=[],
        metavar="DIR",
        help="load the plugin from DIR (repeatable), e.g. a development tree. In isolated "
        "mode it replaces the installed copy; in user mode the installed copy may load too",
    )
    parser.add_argument(
        "--keep-data-instructions",
        action="store_true",
        help="leave the data root's CLAUDE.md, AGENTS.md and .claude/ in the clones",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="prepare the workspaces and print each subject's command and env; spawn nothing",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="spawn one trivial session and report the plugin's visibility only",
    )
    return parser


def _inside(path: Path, other: Path) -> bool:
    try:
        path.resolve().relative_to(other.resolve())
    except ValueError:
        return False
    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_PASSED if exc.code == 0 else EXIT_USAGE

    try:
        every = load_scenarios(SCENARIOS_FILE.read_text(encoding="utf-8"))
        scenarios = select_scenarios(every, args.scenarios)
    except (OSError, ValueError) as exc:
        print(f"error: scenarios: {exc}", file=sys.stderr)
        return EXIT_USAGE
    violations = {s.id: prompt_violations(s) for s in scenarios}
    for sid, found in violations.items():
        for problem in found:
            print(f"error: {sid} prompt {problem}", file=sys.stderr)
    if any(violations.values()):
        return EXIT_USAGE
    if args.budget_usd <= 0 or args.timeout_s <= 0:
        print("error: --budget-usd and --timeout-s must be positive", file=sys.stderr)
        return EXIT_USAGE

    data_root = resolve_data_root(args.data_root, os.environ)
    needs_clone = not args.preflight_only and any(s.workspace == "clone" for s in scenarios)
    if data_root is not None:
        problem = data_root_problem(data_root)
        if problem and (needs_clone or args.data_root is not None):
            print(f"error: {problem}", file=sys.stderr)
            return EXIT_USAGE
        if problem:
            print(f"note: FATHOM_HOME is not watched: {problem}", file=sys.stderr)
            data_root = None
    elif needs_clone:
        print("error: no data root: pass --data-root DIR", file=sys.stderr)
        return EXIT_USAGE

    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    default_out = args.out is None
    out = (args.out or Path(tempfile.gettempdir()) / "fathom-agent-acceptance" / run_id).resolve()
    workspace_base = args.workspace_root.resolve() if args.workspace_root else None
    if workspace_base is not None:
        if _inside(workspace_base, out):
            print(
                "error: --workspace-root must not be inside the output directory", file=sys.stderr
            )
            return EXIT_USAGE
        workspace_base.mkdir(parents=True, exist_ok=True)
    elif args.config == "isolated":
        workspace_base = default_workspace_base(Path(tempfile.gettempdir()), os.environ)
    if args.config == "isolated":
        # A file found here would reach every subject, whatever its configuration directory.
        above = ancestor_instructions(workspace_base or Path(tempfile.gettempdir()))
        if above:
            print(
                "error: instruction files at or above the workspace root would reach every "
                f"subject: {', '.join(map(str, above))}; pass --workspace-root DIR with none "
                "at or above it",
                file=sys.stderr,
            )
            return EXIT_USAGE
    if out.exists() and any(out.iterdir()):
        print(f"error: {out} is not empty; pass another --out or --run-id", file=sys.stderr)
        return EXIT_USAGE

    real_config = real_config_dir(os.environ)
    plugin_dirs = [str(Path(d).resolve()) for d in args.plugin_dir]
    installed = installed_plugin_path(real_config)
    if args.config == "isolated" and not plugin_dirs:
        if installed is None:
            print(
                "error: the fathom plugin is not installed (no entry in "
                f"{real_config / 'plugins' / 'installed_plugins.json'}); install it, pass "
                "--plugin-dir DIR, or use --config user",
                file=sys.stderr,
            )
            return EXIT_ENVIRONMENT
        plugin_dirs = [str(installed)]
    if (
        args.config == "isolated"
        and not args.dry_run
        and not (real_config / CREDENTIAL_FILE).is_file()
    ):
        print(
            f"error: isolated mode copies {CREDENTIAL_FILE} from {real_config}, and there is "
            "none; sign in with claude, or use --config user",
            file=sys.stderr,
        )
        return EXIT_ENVIRONMENT

    if args.preflight_only:
        if args.dry_run:
            cmd = subject_command(
                model=args.model,
                budget_usd=PREFLIGHT_BUDGET_USD,
                effort=args.effort,
                allowed=(PREFLIGHT_TOOL,),
                disallowed=(*DISALLOWED_TOOLS, *PREFLIGHT_DISALLOWED),
                plugin_dirs=plugin_dirs,
            )
            print(f"configuration: {args.config}")
            print(f"command: {format_command(cmd)}")
            print(f"stdin: {PREFLIGHT_PROMPT}")
            print("FATHOM_HOME: unset")
            print("Dry run: nothing spawned.")
            return EXIT_PASSED
        claude = shutil.which("claude")
        if claude is None:
            print("error: claude is not on PATH", file=sys.stderr)
            return EXIT_ENVIRONMENT
        out.mkdir(parents=True, exist_ok=True)
        return run_preflight(
            claude=claude,
            out=out,
            model=args.model,
            effort=args.effort,
            plugin_dirs=plugin_dirs,
            config_mode=args.config,
            real_config=real_config,
            data_root=data_root,
            workspace_base=workspace_base,
        )

    out.mkdir(parents=True, exist_ok=True)
    examples = example_rows([Path(d) for d in plugin_dirs] + ([installed] if installed else []))
    try:
        prepared = [
            prepare(
                s,
                out,
                data_root=data_root,
                base_env=os.environ,
                config_mode=args.config,
                plugin_dirs=plugin_dirs,
                workspace_base=workspace_base,
                keep_instructions=args.keep_data_instructions,
                examples=examples,
            )
            for s in scenarios
        ]
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or ""
        print(f"error: preparing the workspaces failed: {exc} {detail}".strip(), file=sys.stderr)
        return EXIT_ENVIRONMENT
    exposures = {p.scenario.id: exposure_violations(p.scenario, p.shown(), every) for p in prepared}
    print(f"Run {run_id}: {out}")
    if args.dry_run:
        print_plan(
            prepared,
            model=args.model,
            effort=args.effort,
            budget_usd=args.budget_usd,
            exposures=exposures,
        )
    if any(exposures.values()):
        for sid, found in exposures.items():
            for problem in found:
                print(f"error: {sid}: {problem}", file=sys.stderr)
        return EXIT_USAGE
    if args.dry_run:
        return EXIT_PASSED

    claude = shutil.which("claude")
    if claude is None:
        print("error: claude is not on PATH", file=sys.stderr)
        return EXIT_ENVIRONMENT
    markers = output_markers(out, default_out=default_out)
    verdicts: list[dict[str, Any]] = []
    stop_reason: str | None = None
    for p in prepared:
        s = p.scenario
        if stop_reason:
            verdicts.append(
                {"scenario": s.id, "name": s.name, "status": "skipped", "reason": stop_reason}
            )
            continue
        print(f"{s.id} {s.name}: running (workspace {p.workspace})", flush=True)
        if p.fathom_on_path:
            print(f"{s.id}: note: the subject's PATH resolves fathom to {p.fathom_on_path}")
        # Read just before this subject, so a change is charged to the subject that made it.
        before: GitState | None = None
        if data_root is not None:
            with contextlib.suppress(OSError, subprocess.CalledProcessError):
                before = git_state(data_root)
        verdict = run_scenario(
            p,
            claude=claude,
            model=args.model,
            effort=args.effort,
            budget_usd=args.budget_usd,
            timeout_s=args.timeout_s,
            data_root=data_root,
            before=before,
            real_config=real_config,
            out_markers=markers,
        )
        verdicts.append(verdict)
        subject = verdict["subject"]
        print(
            f"{s.id} {s.name}: {verdict['status'].upper()} "
            f"(cost {_money(subject['cost_usd'])}, {subject['wall_s']:.0f} s)",
            flush=True,
        )
        if verdict["status"] == "environment":
            stop_reason = (
                f"Skipped: {s.id} found an environment failure ("
                + "; ".join(verdict["visibility"]["problems"])
                + ")."
            )
    code = exit_code_for(v["status"] for v in verdicts)
    report = out / "report.md"
    report.write_text(
        render_report(
            {
                "run_id": run_id,
                "model": args.model,
                "effort": args.effort,
                "config_mode": args.config,
                "out": str(out),
                "exit_code": code,
            },
            verdicts,
        ),
        encoding="utf-8",
    )
    print(f"Report: {report}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
