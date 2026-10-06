#!/usr/bin/env python
"""Check that a fresh Claude Code agent can use the installed fathom plugin unaided.

Each scenario spawns one headless Claude Code session, the subject, with a user's goal in
plain words and nothing else: no appended system prompt, and no fathom command, flag, path,
skill or MCP tool name in the prompt. Whatever the subject learns about fathom it learns
from what the installed plugin shows it: the skill, the slash commands and the MCP tools.
The harness then judges each session three ways:

- what the session could see: the init event of its stream (an environment fact, reported
  apart from the agent's behaviour);
- what the session did: the tool calls in its stream, classified by the fathom surface each
  one used;
- what is true afterwards: the files in its workspace, the real data root's git state, and
  a ``fathom reconcile`` the harness runs itself.

The real data root is never handed to a subject. A scenario that needs existing data gets a
local clone of it, with the clone's ``origin`` remote removed, and the harness compares the
real data root's ``git status`` and HEAD before and after every subject.

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
    env_for_agent_code,
    hidden_from_children,
    terminate_process_tree,
)

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
SPEND_RAILS = ("--max-run-usd", "--max-spawn-usd", "--max-budget-usd")
# Surfaces whose calls execute fathom. A command call only expands the command's text; the
# engine runs in the Bash call that follows it, which is classified on its own.
EXECUTING = ("cli", "mcp")

# Permissions only: the subject is never shown these lists. ToolSearch loads the schema of
# a deferred tool; without it an MCP tool the CLI defers could be listed and never called.
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
DISALLOWED_TOOLS = ("Bash(git push:*)", "Bash(gh:*)", "WebFetch", "WebSearch")

PREFLIGHT_PROMPT = "Reply with the word ready."
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

# Variables a running Claude Code session sets for the processes it starts. A subject is
# meant to look like a session a user started in a terminal, so none of them is passed on:
# the session markers, the identity of the parent session and its process, the channel to
# the parent's host and its auth refresh, the parent's effort, and the setting that lets a
# session start before its MCP servers connect (under it the init event can report the
# fathom server as pending). The names were read from a desktop-app session's environment.
PARENT_SESSION_VARS = frozenset(
    {
        "CLAUDECODE",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_CODE_HOST_SESSION_ID",
        "CLAUDE_CODE_CHILD_SESSION",
        "CLAUDE_CODE_SESSION_ATTENDED",
        "CLAUDE_CODE_MESSAGING_SOCKET",
        "CLAUDE_CODE_MESSAGING_TOKEN",
        "CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH",
        "CLAUDE_CODE_EXECPATH",
        "CLAUDE_AGENT_SDK_VERSION",
        "CLAUDE_PID",
        "CLAUDE_EFFORT",
        "MCP_CONNECTION_NONBLOCKING",
    }
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


# ---------------------------------------------------------------------------
# The subject's environment and command line
# ---------------------------------------------------------------------------


def subject_env(
    base: Mapping[str, str],
    fathom_home: Path | None,
    *,
    hidden: Sequence[Path] = (),
) -> tuple[dict[str, str], list[str]]:
    """The environment a subject starts with, and the names removed from *base*.

    Starts from :func:`fathom.adapters.claude_cli.env_for_agent_code`, the environment the
    engine gives its own trial spawns: every ``FATHOM_*`` variable, ``PWD``, ``OLDPWD`` and
    the billing and routing variables removed, and no variable whose value names one of the
    *hidden* directories (the real data root). Then the parent session's variables
    (:data:`PARENT_SESSION_VARS`) go, and ``FATHOM_HOME`` is set to *fathom_home*, or left
    unset when it is ``None``. Names are compared case-insensitively, as Windows compares
    them. The removed names are returned without their values, which may be secrets.
    """
    with hidden_from_children(*hidden):
        env = env_for_agent_code(base)
    for name in list(env):
        if name.upper() in PARENT_SESSION_VARS:
            del env[name]
    removed = sorted(name for name in base if name not in env)
    if fathom_home is not None:
        env["FATHOM_HOME"] = str(fathom_home)
    return env, removed


def subject_command(
    *,
    model: str,
    budget_usd: float,
    allowed: Sequence[str] = ALLOWED_TOOLS,
    plugin_dirs: Sequence[str] = (),
) -> list[str]:
    """The ``claude`` argv for one subject. The prompt goes on stdin, as the engine's adapter
    sends it, so no variadic option can swallow it and no shell quoting touches it.

    No system prompt is appended. An empty *allowed* list leaves every tool to the
    headless default-deny.
    """
    cmd = [
        "claude",
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--max-budget-usd",
        f"{budget_usd:g}",
        "--permission-mode",
        "acceptEdits",
        "--no-session-persistence",
    ]
    if allowed:
        cmd += ["--allowedTools", ",".join(allowed)]
    cmd += ["--disallowedTools", ",".join(DISALLOWED_TOOLS)]
    for plugin_dir in plugin_dirs:
        cmd += ["--plugin-dir", str(plugin_dir)]
    return cmd


def format_command(cmd: Sequence[str]) -> str:
    """*cmd* as one line in the host shell's quoting."""
    return subprocess.list2cmdline(list(cmd)) if os.name == "nt" else shlex.join(cmd)


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

    @property
    def is_error(self) -> bool:
        return bool(self.result and self.result["is_error"])

    @property
    def text(self) -> str:
        return str(self.result["text"]) if self.result else ""

    @property
    def succeeded(self) -> bool:
        """A result came back, it is not an error, and an MCP result does not say ``ok`` false."""
        if self.result is None or self.is_error:
            return False
        return not (self.surface == "mcp" and re.search(r'\\?"ok\\?":\s*false', self.text))


@dataclasses.dataclass
class Analysis:
    """What one subject's stream shows."""

    init: dict[str, Any] | None
    calls: list[ToolCall]
    result: dict[str, Any] | None
    malformed_lines: int = 0
    other_events: int = 0

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
            )
        )
    result = next((ev for ev in reversed(events) if ev.get("type") == "result"), None)
    other = sum(1 for ev in events if ev.get("type") not in KNOWN_EVENTS)
    return Analysis(
        init=init, calls=calls, result=result, malformed_lines=malformed, other_events=other
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


_SEGMENT_BREAK = re.compile(r"&&|\|\||[;|\n&]")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = frozenset({"env", "time", "exec", "command", "nohup", "call"})
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
    }
)


def _split(text: str) -> list[str]:
    try:
        return shlex.split(text)
    except ValueError:  # an unbalanced quote: fall back to whitespace
        return text.split()


def _program(token: str) -> str:
    """A command word reduced to its program name: no directory, no ``.exe``, lower case."""
    name = re.split(r"[\\/]", token.strip("(){}"))[-1].lower()
    return name.removesuffix(".exe")


def _fathom_argv(tokens: Sequence[str]) -> list[str] | None:
    """The arguments after fathom's entry point in one shell segment, or ``None``.

    The entry point is ``-m fathom`` anywhere (``python -m fathom``, ``uv run ... python -m
    fathom``), a command word that is the ``fathom`` executable, or ``fathom`` launched by
    ``uv run``, ``uv tool run`` or ``uvx``.
    """
    for i in range(len(tokens) - 1):
        if tokens[i] == "-m" and tokens[i + 1] == PLUGIN:
            return list(tokens[i + 2 :])
    i = 0
    while i < len(tokens) and (_ASSIGNMENT.match(tokens[i]) or tokens[i] in _WRAPPERS):
        i += 1
    if i >= len(tokens):
        return None
    program = _program(tokens[i])
    if program == PLUGIN:
        return list(tokens[i + 1 :])
    if program not in ("uv", "uvx"):
        return None
    j = i + 1
    if program == "uv":
        while j < len(tokens) and tokens[j] in ("run", "tool"):
            j += 1
    while j < len(tokens) and tokens[j].startswith("-"):
        j += 2 if tokens[j] in _UV_VALUE_OPTIONS else 1
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


def cli_invocations(command: str) -> list[Invocation]:
    """Every fathom invocation in a shell command line, in order ([] when there is none).

    The line is cut at ``&&``, ``||``, ``;``, ``|``, ``&`` and newlines, and each segment is
    read as one command. A word that merely contains "fathom" (a path, a grep pattern, a
    quoted string) is not an invocation.
    """
    out: list[Invocation] = []
    for segment in _SEGMENT_BREAK.split(command):
        argv = _fathom_argv(_split(segment))
        if argv is not None:
            out.append(cli_invocation(argv))
    return out


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
    mcp_connected_late: bool  # pending at init, then a successful call
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
        if not self.mcp_connected:
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
    of its tools succeeded; the verdict says so.
    """
    init = analysis.init
    servers = [
        s
        for s in _init_list(init, "mcp_servers")
        if isinstance(s, dict) and str(s.get("name", "")).startswith(MCP_SERVER_PREFIX)
    ]
    at_init = any(str(s.get("status", "")).lower() == "connected" for s in servers)
    later = any(c.surface == "mcp" and c.succeeded for c in analysis.calls)
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
        commands_listed=listed,
        commands_missing=[c for c in expected_commands if c not in listed],
        skill_listed=f"{PLUGIN}:{SKILL}" in skills or SKILL in skills,
        plugins=plugins,
    )


def behaviour(analysis: Analysis) -> dict[str, Any]:
    """Informational facts about how the subject used fathom; none of them is pass/fail.

    ``smoke_before_run``, ``plan_before_run`` and ``budget_rail_used`` are ``None`` when the
    subject made no paid run.
    """
    ops = [(c.index, c.surface, inv) for c in analysis.calls if c.surface for inv in c.invocations]
    paid = [(i, inv) for i, surface, inv in ops if surface in EXECUTING and inv.op == PAID_RUN]
    first_paid = paid[0][0] if paid else None

    def before_first_paid(op: str) -> bool | None:
        if first_paid is None:
            return None
        return any(i < first_paid and s in EXECUTING and inv.op == op for i, s, inv in ops)

    first = analysis.first_fathom_index
    first_call = analysis.calls[first] if first is not None else None
    surfaces: list[str] = []
    for call in analysis.fathom_calls:
        if call.surface and call.surface not in surfaces:
            surfaces.append(call.surface)
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
        "budget_rail_used": (
            any(a.split("=", 1)[0] in SPEND_RAILS for _, inv in paid for a in inv.args)
            if paid
            else None
        ),
        "smoke_before_run": before_first_paid("smoke"),
        "plan_before_run": before_first_paid(DRY_RUN),
    }


def fathom_errors(analysis: Analysis) -> list[dict[str, Any]]:
    """The fathom-surface calls whose result was an error, with an excerpt of each."""
    return [
        {"index": c.index, "surface": c.surface, "tool": c.name, "text": c.text[:ERROR_EXCERPT]}
        for c in analysis.fathom_calls
        if c.is_error
    ]


# ---------------------------------------------------------------------------
# Ground truth (pure scans of files and of git's output)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GitState:
    head: str
    status: str


@dataclasses.dataclass(frozen=True)
class Outcome:
    """A command the harness ran itself."""

    exit_code: int | None
    output: str


@dataclasses.dataclass
class RootScan:
    """A data root found under a workspace, and what it holds."""

    path: Path
    banks: list[str]
    tasks: list[str]  # "<bank>/<task>"
    tasks_with_verifier: list[str]
    arms: list[str]  # scenario files declaring a strategy, relative to the root
    completed_trials: int
    configs: list[str]  # distinct config_hash values of the completed trials
    run_rows: int
    spend_usd: float  # cost_usd_est summed over every ledger row that carries one
    scorecards: list[str]


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


def _read_toml(path: Path) -> dict[str, Any] | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None


def find_data_roots(workspace: Path) -> list[Path]:
    """Directories under *workspace* (itself included) whose ``fathom.toml`` has a
    ``[data_root]`` table, shallowest first."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(workspace):
        dirnames[:] = sorted(d for d in dirnames if d not in _SCAN_SKIP)
        if "fathom.toml" in filenames:
            data = _read_toml(Path(dirpath) / "fathom.toml")
            if data is not None and isinstance(data.get("data_root"), dict):
                found.append(Path(dirpath))
    return sorted(found, key=lambda p: (len(p.parts), str(p)))


def _ledger_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "ledger").glob("*.jsonl")):
        events, _ = parse_lines(path.read_text(encoding="utf-8", errors="replace").splitlines())
        rows.extend(events)
    return rows


def scan_data_root(root: Path) -> RootScan:
    """What *root* holds: banks, tasks and their verifiers, arms, ledger rows, scorecards."""
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
    arms = sorted(
        p.relative_to(root).as_posix()
        for p in (root / "scenarios").rglob("*.toml")
        if isinstance((_read_toml(p) or {}).get("strategy"), str)
    )
    rows = _ledger_rows(root)
    completed = [
        r for r in rows if r.get("kind", "trial") == "trial" and r.get("status") == "completed"
    ]
    costs = [r.get("cost_usd_est") for r in rows]
    spend = sum(c for c in costs if isinstance(c, int | float) and not isinstance(c, bool))
    report = root / "report"
    return RootScan(
        path=root,
        banks=banks,
        tasks=tasks,
        tasks_with_verifier=verified,
        arms=arms,
        completed_trials=len(completed),
        configs=sorted({str(r["config_hash"]) for r in completed if r.get("config_hash")}),
        run_rows=sum(1 for r in rows if r.get("kind") == "run"),
        spend_usd=float(spend),
        scorecards=sorted(
            p.name for p in report.glob("scorecard-*.md") if p.is_file() and p.stat().st_size
        ),
    )


def choose_root(roots: Sequence[RootScan]) -> RootScan | None:
    """The data root a measurement most likely went to: most completed trials, then most
    arms, then the shallowest."""
    if not roots:
        return None
    return max(roots, key=lambda r: (r.completed_trials, len(r.arms), -len(r.path.parts)))


# ---------------------------------------------------------------------------
# Checks (pure)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Facts:
    """What the harness observed outside the stream once the subject exited."""

    timed_out: bool = False
    workspace: Path | None = None
    data_root_before: GitState | None = None
    data_root_after: GitState | None = None
    clone_changes: list[str] | None = None  # changed paths in the clone
    banks: list[str] = dataclasses.field(default_factory=list)  # in the clone, before
    roots: list[RootScan] = dataclasses.field(default_factory=list)
    reconcile: Outcome | None = None


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
    if ctx.facts.timed_out:
        return False, "the session hit the wall-clock limit and was killed"
    if result is None:
        return False, "the stream has no result event"
    if result.get("is_error"):
        return False, f"the session ended in error ({result.get('subtype', 'no subtype')})"
    return True, f"{result.get('subtype', 'success')} after {result.get('num_turns', '?')} turns"


def check_data_root_untouched(ctx: Context) -> tuple[bool, str]:
    before, after = ctx.facts.data_root_before, ctx.facts.data_root_after
    if before is None or after is None:
        return False, "the real data root's git state was not recorded"
    changed = []
    if before.head != after.head:
        changed.append(f"HEAD moved from {before.head[:12]} to {after.head[:12]}")
    if before.status != after.status:
        changed.append(
            f"git status changed ({len(porcelain_paths(before.status))} entries before, "
            f"{len(porcelain_paths(after.status))} after)"
        )
    if changed:
        return False, "the real data root changed: " + "; ".join(changed)
    return True, f"HEAD {before.head[:12]} and git status unchanged"


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


def check_no_paid_run(ctx: Context) -> tuple[bool, str]:
    paid = ctx.analysis.executed(PAID_RUN)
    if paid:
        return False, "paid runs: " + _listing([f"#{c.index} {c.summary}" for c in paid])
    return True, "no fathom run without --dry-run"


def check_reconcile_ran(ctx: Context) -> tuple[bool, str]:
    calls = ctx.analysis.executed("reconcile")
    ran = [c for c in calls if c.succeeded or "RECONCILE:" in c.text]
    if ran:
        call = ran[0]
        state = "exit 0" if call.succeeded else "ran and reported a disagreement"
        return True, f"#{call.index} {call.surface}: {state}"
    if calls:
        return (
            False,
            f"{len(calls)} reconcile call(s), none of which ran: {_oneline(calls[0].text)}",
        )
    return False, "no reconcile call"


def check_plan_ran(ctx: Context) -> tuple[bool, str]:
    calls = ctx.analysis.executed(DRY_RUN)
    ran = [c for c in calls if c.succeeded]
    if ran:
        return True, f"#{ran[0].index} {ran[0].surface}: {ran[0].summary}"
    if calls:
        return False, f"{len(calls)} dry-run call(s), none succeeded: {_oneline(calls[0].text)}"
    return False, "no dry-run plan (CLI run --dry-run or the MCP plan tool)"


def check_answer_names_banks(ctx: Context) -> tuple[bool, str]:
    banks = ctx.facts.banks
    if not banks:
        return False, "the clone has no ledger/<bank>.jsonl, so there is nothing to name"
    text = str((ctx.analysis.result or {}).get("result") or "")
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
        f"{root.completed_trials} completed trial row(s) across "
        f"{len(root.configs)} config_hash value(s)"
    )
    return root.completed_trials >= 2 and len(root.configs) >= 2, evidence


def check_measurement_within_budget(ctx: Context) -> tuple[bool, str]:
    root = _root_or_none(ctx)
    if root is None:
        return False, "no data root"
    limit = ctx.scenario.measurement_budget_usd * 1.5
    evidence = (
        f"ledger cost_usd_est ${root.spend_usd:.2f} over {root.run_rows} run row(s); "
        f"limit ${limit:.2f} (1.5 x the ${ctx.scenario.measurement_budget_usd:.2f} asked for)"
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
# wants from the ones below `session_finished` and `data_root_untouched`, which the harness
# adds itself (the second for clone workspaces only).
CHECKS: dict[str, tuple[str, CheckFn]] = {
    "session_finished": ("behaviour", check_session_finished),
    "data_root_untouched": ("ground truth", check_data_root_untouched),
    "no_ledger_change": ("ground truth", check_no_ledger_change),
    "no_paid_run": ("ground truth", check_no_paid_run),
    "reconcile_ran": ("behaviour", check_reconcile_ran),
    "plan_ran": ("behaviour", check_plan_ran),
    "answer_names_banks": ("answer", check_answer_names_banks),
    "fathom_used": ("behaviour", check_fathom_used),
    "data_root_created": ("ground truth", check_data_root_created),
    "bank_authored": ("ground truth", check_bank_authored),
    "arms_authored": ("ground truth", check_arms_authored),
    "trials_completed": ("ground truth", check_trials_completed),
    "measurement_within_budget": ("ground truth", check_measurement_within_budget),
    "reconcile_passes": ("ground truth", check_reconcile_passes),
    "scorecard_rendered": ("ground truth", check_scorecard_rendered),
}
AUTOMATIC_CHECKS = ("session_finished", "data_root_untouched")
CLONE_CHECKS = frozenset({"data_root_untouched", "no_ledger_change", "answer_names_banks"})
WORKSPACE_ROOT_CHECKS = frozenset(
    {
        "data_root_created",
        "bank_authored",
        "arms_authored",
        "trials_completed",
        "measurement_within_budget",
        "reconcile_passes",
        "scorecard_rendered",
    }
)


def checks_for(scenario: Scenario) -> list[str]:
    """The checks a scenario runs: the automatic ones, then the ones it names."""
    names = ["session_finished"]
    if scenario.workspace == "clone":
        names.append("data_root_untouched")
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


def verdict_record(
    *,
    scenario: Scenario,
    status: str,
    workspace: Path,
    fathom_home: Path | None,
    command: Sequence[str],
    unset: Sequence[str],
    exit_code: int | None,
    timed_out: bool,
    wall_s: float,
    analysis: Analysis,
    visibility: Visibility,
    checks: Sequence[Check],
) -> dict[str, Any]:
    """The ``verdict.json`` content for one scenario."""
    result = analysis.result or {}
    return {
        "scenario": scenario.id,
        "name": scenario.name,
        "status": status,
        "workspace": str(workspace),
        "fathom_home": str(fathom_home) if fathom_home else None,
        "command": list(command),
        "env_unset": list(unset),
        "subject": {
            "exit_code": exit_code,
            "timed_out": timed_out,
            "wall_s": round(wall_s, 1),
            "duration_ms": result.get("duration_ms"),
            "cost_usd": result.get("total_cost_usd"),
            "turns": result.get("num_turns"),
            "model": (analysis.init or {}).get("model"),
            "result_subtype": result.get("subtype"),
            "is_error": result.get("is_error"),
            "permission_denials": result.get("permission_denials") or [],
        },
        "visibility": {**dataclasses.asdict(visibility), "problems": visibility.problems()},
        "checks": [dataclasses.asdict(c) for c in checks],
        "behaviour": behaviour(analysis),
        "fathom_errors": fathom_errors(analysis),
        "stream": {
            "tool_calls": len(analysis.calls),
            "malformed_lines": analysis.malformed_lines,
            "other_events": analysis.other_events,
        },
        "final_answer": str(result.get("result") or ""),
    }


def _money(value: Any) -> str:
    return f"${value:.2f}" if isinstance(value, int | float) else "n/a"


def render_report(run: Mapping[str, Any], verdicts: Sequence[Mapping[str, Any]]) -> str:
    """``report.md``: the summary table, environment visibility, then each scenario."""
    lines = [
        f"# fathom agent acceptance, run {run['run_id']}",
        "",
        f"Model: {run['model']}. Exit code: {run['exit_code']}. Output: `{run['out']}`.",
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
    """HEAD and ``git status`` of *repo*, read without taking optional locks, so the read
    writes nothing (no index refresh)."""
    head = _git("rev-parse", "HEAD", cwd=repo).strip()
    status = _git("status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=repo)
    return GitState(head=head, status=status)


@dataclasses.dataclass
class Prepared:
    """A scenario ready to spawn."""

    scenario: Scenario
    directory: Path  # <out>/<id>-<name>/: transcript.jsonl, stderr.txt, verdict.json
    workspace: Path  # the subject's working directory
    clone: Path | None
    fathom_home: Path | None
    env: dict[str, str]
    unset: list[str]
    banks: list[str]


def prepare(
    scenario: Scenario, out: Path, data_root: Path | None, base_env: Mapping[str, str]
) -> Prepared:
    """Create the scenario's directory and workspace; clone the data root if it needs one.

    The clone's ``origin`` remote is removed so nothing in it points back at the real data
    root.
    """
    directory = out / scenario.dirname
    workspace = directory / "workspace"
    workspace.mkdir(parents=True)
    clone: Path | None = None
    banks: list[str] = []
    if scenario.workspace == "clone":
        if data_root is None:
            raise RuntimeError(f"{scenario.id} needs a data root to clone")
        clone = workspace / "data"
        _git("clone", "--quiet", "--local", "--no-hardlinks", str(data_root), str(clone))
        _git("remote", "remove", "origin", cwd=clone)
        banks = ledger_banks(clone)
    fathom_home = clone if scenario.fathom_home else None
    hidden = [data_root] if data_root is not None else []
    env, unset = subject_env(base_env, fathom_home, hidden=hidden)
    return Prepared(scenario, directory, workspace, clone, fathom_home, env, unset, banks)


@dataclasses.dataclass(frozen=True)
class SubjectRun:
    exit_code: int | None
    timed_out: bool
    wall_s: float


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
) -> SubjectRun:
    """Spawn one subject; stream stdout to *transcript* and stderr to *stderr*.

    On the wall-clock limit the whole process tree is killed (``taskkill /T /F`` on
    Windows, the process group elsewhere), as the engine's adapter does.
    """
    popen_kwargs: dict[str, Any] = {}
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    started = time.monotonic()
    timed_out = False
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
        if proc.stdin is not None:
            # OSError: the CLI exited before reading its prompt; its stderr says why.
            with contextlib.suppress(OSError):
                proc.stdin.write(prompt.encode("utf-8"))
                proc.stdin.close()
        try:
            code: int | None = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            terminate_process_tree(proc.pid)
            try:
                code = proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                code = proc.wait()
    return SubjectRun(exit_code=code, timed_out=timed_out, wall_s=time.monotonic() - started)


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


def collect_facts(
    prepared: Prepared,
    *,
    analysis: Analysis,
    run: SubjectRun,
    data_root: Path | None,
    before: GitState | None,
) -> Facts:
    """Read the ground truth once the subject has exited."""
    scenario = prepared.scenario
    facts = Facts(timed_out=run.timed_out, workspace=prepared.workspace, banks=prepared.banks)
    if scenario.workspace == "clone" and data_root is not None:
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
    if WORKSPACE_ROOT_CHECKS & set(scenario.checks):
        facts.roots = [scan_data_root(p) for p in find_data_roots(prepared.workspace)]
        chosen = choose_root(facts.roots)
        if chosen is not None and "reconcile_passes" in scenario.checks:
            paths = [Path(str(p["path"])) for p in fathom_plugins(analysis.init) if p.get("path")]
            env, _ = subject_env(os.environ, None)
            facts.reconcile = run_reconcile(chosen.path, paths[0] if paths else None, env)
    return facts


def run_scenario(
    prepared: Prepared,
    *,
    claude: str,
    model: str,
    budget_usd: float,
    plugin_dirs: Sequence[str],
    timeout_s: float,
    data_root: Path | None,
    before: GitState | None,
) -> dict[str, Any]:
    """Spawn one subject, judge it, and write its ``verdict.json``. Returns the verdict."""
    scenario = prepared.scenario
    cmd = subject_command(model=model, budget_usd=budget_usd, plugin_dirs=plugin_dirs)
    transcript = prepared.directory / "transcript.jsonl"
    run = run_subject(
        claude,
        cmd,
        prompt=scenario.prompt,
        cwd=prepared.workspace,
        env=prepared.env,
        transcript=transcript,
        stderr=prepared.directory / "stderr.txt",
        timeout_s=timeout_s,
    )
    analysis = analyze(read_transcript(transcript), doc_roots=plugin_dirs)
    visibility = assess_visibility(analysis, plugin_commands(fathom_plugins(analysis.init)))
    facts = collect_facts(prepared, analysis=analysis, run=run, data_root=data_root, before=before)
    checks = evaluate(scenario, analysis, facts)
    verdict = verdict_record(
        scenario=scenario,
        status=status_of(visibility, checks),
        workspace=prepared.workspace,
        fathom_home=prepared.fathom_home,
        command=cmd,
        unset=prepared.unset,
        exit_code=run.exit_code,
        timed_out=run.timed_out,
        wall_s=run.wall_s,
        analysis=analysis,
        visibility=visibility,
        checks=checks,
    )
    (prepared.directory / "verdict.json").write_text(
        json.dumps(verdict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return verdict


def run_preflight(
    *,
    claude: str,
    out: Path,
    model: str,
    plugin_dirs: Sequence[str],
    data_root: Path | None,
) -> int:
    """One trivial session from an empty directory; report the plugin's visibility only."""
    directory = out / "preflight"
    workspace = directory / "workspace"
    workspace.mkdir(parents=True)
    env, _ = subject_env(os.environ, data_root)
    cmd = subject_command(
        model=model, budget_usd=PREFLIGHT_BUDGET_USD, allowed=(), plugin_dirs=plugin_dirs
    )
    transcript = directory / "transcript.jsonl"
    run = run_subject(
        claude,
        cmd,
        prompt=PREFLIGHT_PROMPT,
        cwd=workspace,
        env=env,
        transcript=transcript,
        stderr=directory / "stderr.txt",
        timeout_s=PREFLIGHT_TIMEOUT_S,
    )
    analysis = analyze(read_transcript(transcript), doc_roots=plugin_dirs)
    visibility = assess_visibility(analysis, plugin_commands(fathom_plugins(analysis.init)))
    record = {
        "status": "pass" if visibility.ok else "environment",
        "exit_code": run.exit_code,
        "timed_out": run.timed_out,
        "cost_usd": (analysis.result or {}).get("total_cost_usd"),
        "visibility": {**dataclasses.asdict(visibility), "problems": visibility.problems()},
    }
    (directory / "verdict.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Preflight transcript: {transcript}")
    print(f"MCP server: {', '.join(visibility.mcp_servers) or 'not listed'}")
    print(f"Commands listed: {', '.join(visibility.commands_listed) or 'none'}")
    print(f"Skill listed: {'yes' if visibility.skill_listed else 'no'}")
    for plugin in visibility.plugins:
        print(f"Plugin: {plugin.get('name')} {plugin.get('version')} at {plugin.get('path')}")
    if visibility.ok:
        print("PREFLIGHT: OK (the plugin is visible)")
        return EXIT_PASSED
    print("PREFLIGHT: ENVIRONMENT FAILURE: " + "; ".join(visibility.problems()))
    return EXIT_ENVIRONMENT


def print_plan(
    prepared: Sequence[Prepared], *, model: str, budget_usd: float, plugin_dirs: Sequence[str]
) -> None:
    """What a run would spawn, without spawning it."""
    cmd = subject_command(model=model, budget_usd=budget_usd, plugin_dirs=plugin_dirs)
    for p in prepared:
        s = p.scenario
        print(f"--- {s.id} {s.name} ({s.workspace} workspace)")
        print(f"cwd: {p.workspace}")
        if p.clone is not None:
            print(f"clone: {p.clone} ({len(p.banks)} bank(s) with a ledger)")
        print(f"FATHOM_HOME: {p.fathom_home if p.fathom_home else 'unset'}")
        print(f"env unset: {', '.join(p.unset) or 'nothing'}")
        print(f"command: {format_command(cmd)}")
        print("stdin (the prompt):")
        for line in s.prompt.splitlines() or [""]:
            print(f"    {line}")
        print(f"checks: {', '.join(checks_for(s))}")
        print()
    spend = [p.scenario for p in prepared if p.scenario.measurement_budget_usd > 0]
    print(
        f"Subject sessions: {len(prepared)}, each capped at ${budget_usd:.2f} by "
        f"--max-budget-usd (worst case ${len(prepared) * budget_usd:.2f})."
    )
    for s in spend:
        print(
            f"{s.id} also spends on its own fathom trials, outside that cap: the prompt allows "
            f"${s.measurement_budget_usd:.2f}, and its check fails above "
            f"${s.measurement_budget_usd * 1.5:.2f}."
        )
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
        "--data-root",
        type=Path,
        default=None,
        help="the data root to clone for clone scenarios (default: $FATHOM_HOME); "
        "it is read, never modified",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output directory (default: <temp>/fathom-agent-acceptance/<run id>)",
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
        help="also load a plugin from DIR (repeatable), e.g. a development tree; the "
        "installed plugin may load as well",
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_PASSED if exc.code == 0 else EXIT_USAGE

    try:
        scenarios = select_scenarios(
            load_scenarios(SCENARIOS_FILE.read_text(encoding="utf-8")), args.scenarios
        )
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
    if needs_clone or (args.preflight_only and data_root is not None):
        problem = (
            data_root_problem(data_root)
            if data_root is not None
            else "no data root: pass --data-root DIR"
        )
        if problem:
            print(f"error: {problem}", file=sys.stderr)
            return EXIT_USAGE

    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    out = (args.out or Path(tempfile.gettempdir()) / "fathom-agent-acceptance" / run_id).resolve()
    if out.exists() and any(out.iterdir()):
        print(f"error: {out} is not empty; pass another --out or --run-id", file=sys.stderr)
        return EXIT_USAGE
    out.mkdir(parents=True, exist_ok=True)
    plugin_dirs = [str(Path(d).resolve()) for d in args.plugin_dir]

    if args.preflight_only:
        if args.dry_run:
            cmd = subject_command(
                model=args.model,
                budget_usd=PREFLIGHT_BUDGET_USD,
                allowed=(),
                plugin_dirs=plugin_dirs,
            )
            print(f"command: {format_command(cmd)}")
            print(f"stdin: {PREFLIGHT_PROMPT}")
            print(f"FATHOM_HOME: {data_root or 'unset'}")
            print("Dry run: nothing spawned.")
            return EXIT_PASSED
        claude = shutil.which("claude")
        if claude is None:
            print("error: claude is not on PATH", file=sys.stderr)
            return EXIT_ENVIRONMENT
        return run_preflight(
            claude=claude, out=out, model=args.model, plugin_dirs=plugin_dirs, data_root=data_root
        )

    before: GitState | None = None
    if needs_clone and data_root is not None:
        try:
            before = git_state(data_root)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"error: cannot read the data root's git state: {exc}", file=sys.stderr)
            return EXIT_ENVIRONMENT
    try:
        prepared = [prepare(s, out, data_root, os.environ) for s in scenarios]
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or ""
        print(f"error: preparing the workspaces failed: {exc} {detail}".strip(), file=sys.stderr)
        return EXIT_ENVIRONMENT
    print(f"Run {run_id}: {out}")
    if args.dry_run:
        print_plan(prepared, model=args.model, budget_usd=args.budget_usd, plugin_dirs=plugin_dirs)
        return EXIT_PASSED

    claude = shutil.which("claude")
    if claude is None:
        print("error: claude is not on PATH", file=sys.stderr)
        return EXIT_ENVIRONMENT
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
        if before is not None and data_root is not None and s.workspace == "clone":
            # Compared with the state just before this subject, so a change is charged to
            # the subject that made it.
            with contextlib.suppress(OSError, subprocess.CalledProcessError):
                before = git_state(data_root)
        verdict = run_scenario(
            p,
            claude=claude,
            model=args.model,
            budget_usd=args.budget_usd,
            plugin_dirs=plugin_dirs,
            timeout_s=args.timeout_s,
            data_root=data_root,
            before=before,
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
            {"run_id": run_id, "model": args.model, "out": str(out), "exit_code": code}, verdicts
        ),
        encoding="utf-8",
    )
    print(f"Report: {report}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
