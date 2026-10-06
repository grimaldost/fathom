"""Subscription Claude CLI adapter — vendored spawn core.

Vendored from an earlier eval harness's runner per
``docs/adr/0004-vendor-claude-runner-core.md``: the proven, debugged spawn
mechanics are *copied*, not depended on (that harness lives in a repository whose
tools fathom may itself measure), and refactored behind the ``Runner`` protocol
(ADR-0001).  The isolation properties are preserved:

* a temp ``CLAUDE_CONFIG_DIR`` holding only the copied credential — no CLAUDE.md,
  settings.json, or history leaks user context into the supposedly clean arms;
* headless **default-deny**: the command carries no ``--permission-mode`` and no
  ``--dangerously-skip-permissions`` (``bypassPermissions`` auto-approves every
  tool and nullifies the allowlist, so a spawn could write outside its
  workspace); the explicit allow/disallow lists are the actual boundary;
* a spawn environment without the variables that would reroute billing, and
  without fathom's own state: its ``FATHOM_*`` variables, the ``PWD`` /
  ``OLDPWD`` it was started with, and any value naming the data root
  (:func:`make_spawn_env`);
* an argv that names no file under the data root: a trial's runner copies the
  arm's ``[context]`` body and ``[plugins]`` mounts into a directory of the
  spawn's own and passes the copies (:func:`stage_arm_files`);
* ``--output-format stream-json`` parsing that tolerates a stream cut off
  mid-line on timeout;
* retry with a cap on transient (server/network) failures only.

Divergence from the original is expected and managed deliberately, not synced
automatically.  Adaptations to fit the protocol: the skill-activation /
written-text extraction is dropped (the trigger axis is a v1 non-goal); a
``--effort`` flag is added (cross-arm parity, spec §5); auth and subscription
usage-limit responses are classified as **infrastructure** errors so they never
score and never burn a trial's error-retry budget; and a partial stream recovers
what economy it can from assistant messages.

Stdlib only.  The subprocess boundary is injectable so every test runs with a
stub — no real spawns here (that is the smoke gate's job, spec §11).
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import time
import warnings
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from fathom.adapters.base import ExitStatus, RunRecord

if TYPE_CHECKING:
    from fathom.scenario import ResolvedScenario

# stderr/stdout signatures that justify a retry (transient server/network
# failures that a later attempt may clear).
_TRANSIENT = re.compile(
    r"(429|529|overloaded|rate.?limit|\b5\d\d\b|ECONNRESET|ETIMEDOUT|connection reset)",
    re.IGNORECASE,
)

# Auth/credential failures: the subscription login is broken or expired.  Never
# a task outcome and never retryable — more attempts cannot fix auth.
_AUTH = re.compile(
    r"(invalid api key"
    r"|authentication.{0,20}fail"
    r"|not logged ?in"
    r"|please run.{0,20}/?login"
    r"|unauthorized"
    r"|invalid.{0,20}credential"
    r"|oauth.{0,20}(expired|invalid)"
    r"|credit balance is too low)",
    re.IGNORECASE,
)

# Subscription usage-limit / quota exhaustion: a hard cap distinct from a
# transient 429.  Classified infrastructure so it stops the matrix cleanly
# (§10) instead of scoring or burning the trial's retry budget.
_USAGE_LIMIT = re.compile(
    r"(usage limit"
    r"|usage cap"
    r"|reached your (usage |monthly |weekly )?limit"
    r"|limit reached"
    r"|quota (exceeded|exhausted)"
    r"|out of (credits|quota)"
    r"|claude usage limit"
    # Session limit: without this the refusal scores as an ERRORED trial and
    # the matrix consumes many cells burning money unproductively.
    r"|session limit"
    r"|upgrade to (pro|max))",
    re.IGNORECASE,
)

# Auth needs exactly the credential file.  Everything else at the top level of
# ~/.claude leaks user context into the supposedly clean arms: CLAUDE.md carries
# real repo paths and discipline text, settings.json carries permission grants,
# history.jsonl carries past prompts.
_CONFIG_COPY_ALLOWLIST = frozenset({".credentials.json"})


# ---------------------------------------------------------------------------
# Isolation — credential-only temp CLAUDE_CONFIG_DIR (vendored verbatim in spirit)
# ---------------------------------------------------------------------------


def make_isolated_config(real_config: str | None = None, settings_file: str | None = None) -> str:
    """Create a temp CLAUDE_CONFIG_DIR that is authenticated and nothing else.

    Only the credential file is copied FROM THE REAL CONFIG — no CLAUDE.md, no
    settings.json, no history, no plugins.  Caller cleans up with
    :func:`cleanup_dir`.

    ``settings_file`` is an OPTIONAL scenario-declared settings.json written into
    the dir as ``settings.json`` — an explicit per-arm treatment (e.g. a
    user-scope PreToolUse hook which, unlike a plugin hook, DOES fire in headless
    ``claude -p``). It is the arm's own declaration, not the user's real
    settings.json (which stays excluded — the point of the allowlist).
    """
    real = Path(real_config or (Path.home() / ".claude"))
    dest = Path(tempfile.mkdtemp(prefix="fathom_cfg_"))
    for name in _CONFIG_COPY_ALLOWLIST:
        src = real / name
        if src.is_file():
            # locked/unreadable; the smoke gate catches a dead config
            with contextlib.suppress(OSError):
                shutil.copy2(src, dest / name)
    if settings_file:
        # missing/unreadable; the factory warns and the arm degrades to control
        with contextlib.suppress(OSError):
            shutil.copy2(settings_file, dest / "settings.json")
    return str(dest)


def cleanup_dir(path: str, attempts: int = 4) -> None:
    """Best-effort recursive delete; tolerates Windows file locks from claude."""
    for _ in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError:
            time.sleep(0.5)


# Names left out of a staged plugin tree: the ones the plugin's tree_sha skips (version
# control, caches, a local virtual environment and Claude Code's own cache markers). The
# copy holds what enters config_hash, and a virtual environment would carry the absolute
# paths of the original.
_STAGE_SKIP: frozenset[str] = frozenset({"__pycache__", ".venv", ".git", ".in_use", ".orphaned_at"})

# The directory name a staged plugin copy takes when its manifest names the plugin.
STAGED_PLUGIN_DIRNAME = "plugin"


def _staged_mount_name(source: Path) -> str:
    """The directory name for the copy of the plugin mounted from *source*.

    A plugin whose ``.claude-plugin/plugin.json`` gives a name is known by that name,
    so its copy takes the fixed :data:`STAGED_PLUGIN_DIRNAME`: the directory an author
    mounts is often named after the arm, and the argv and the skill base directory
    Claude Code shows the model would otherwise carry it. Without a manifest name,
    Claude Code takes the plugin's name from its directory, so the copy keeps it; that
    name is then the plugin's identity, which the model sees in any case.
    """
    try:
        meta = json.loads((source / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = None
    if isinstance(meta, dict) and meta.get("name"):
        return STAGED_PLUGIN_DIRNAME
    return source.name or STAGED_PLUGIN_DIRNAME


def stage_arm_files(
    dest: Path, *, inject: str | None, plugin_dirs: Sequence[str]
) -> tuple[str | None, tuple[str, ...]]:
    """Copy the arm's ``[context]`` body and ``[plugins]`` mounts into *dest*.

    Returns the paths to pass in the argv instead of the declared ones. A scenario
    declares these files under the data root, and whatever the argv names, the agent
    can learn: a shell grant reads the process table, and Claude Code tells the model a
    loaded skill's base directory. The copies live in a directory of the spawn's own.
    Only paths change: config_hash is taken over the files' content, so no hash or
    resume key moves.

    A declared file or directory that does not exist is not copied, and its staged
    path, which does not exist either, is passed on: the CLI meets the same missing
    file it would have met before, without the declared path. Symbolic links are
    copied as the files they point to, so no link target reaches the copy. A copy that
    fails raises ``OSError``.

    A mount's copy leaves out the names in :data:`_STAGE_SKIP` (``.git``, ``.venv``,
    ``__pycache__`` and Claude Code's cache markers) and is named as
    :func:`_staged_mount_name` says. A plugin that needs one of the left-out names, or
    a path outside its own directory, does not work from the copy.
    """
    staged_inject: str | None = None
    if inject:
        source = Path(inject)
        target = dest / f"context{source.suffix}"
        if source.is_file():
            shutil.copyfile(source, target)
        staged_inject = str(target)
    staged_mounts: list[str] = []
    for index, mount in enumerate(plugin_dirs):
        source = Path(mount)
        # Each mount gets a slot of its own, so two mounts cannot collide.
        target = dest / f"plugin-{index}" / _staged_mount_name(source)
        if source.is_dir():
            shutil.copytree(
                source,
                target,
                ignore=lambda _dir, names: {n for n in names if n in _STAGE_SKIP},
                ignore_dangling_symlinks=True,
            )
        staged_mounts.append(str(target))
    return staged_inject, tuple(staged_mounts)


# Host env vars that would divert a spawn OFF the copied subscription credential:
# an API key / auth token bills the API account instead of the plan, and a base-URL
# override or Bedrock/Vertex routing sends the spawn to a different backend entirely.
# Any of them present in the host env would silently change WHO pays and WHAT model
# actually answers — breaking both the isolation claim (ADR-0004) and USD comparability
# across arms — so they are stripped from every spawn env.
_SPAWN_ENV_STRIP: frozenset[str] = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_BEDROCK_BASE_URL",
        "ANTHROPIC_VERTEX_BASE_URL",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "AWS_BEARER_TOKEN_BEDROCK",
    }
)


# fathom's own variables. fathom passes itself state through them — FATHOM_HOME names the
# data root, which holds every task's reference material; FATHOM_STREAM_DIR and
# FATHOM_STREAM_TAG tell the adapter where to keep a trial's raw stream, and the tag
# carries the arm's name — and none of it is for the agent under test: an agent that can
# read the data root can read the answers, and one that knows its arm can write it into
# the workspace the blind verifier scores. So every variable under the prefix is stripped
# from every spawn env, including names fathom does not use yet. Names are compared
# case-insensitively, as Windows compares them.
HARNESS_ENV_PREFIX = "FATHOM_"

# The directory fathom was started in, as the starting shell recorded it. One way fathom
# finds its data root is by being started inside it, and moving into the data root for a
# command (`contextlib.chdir`) changes the process's working directory but not these
# variables, so PWD — and OLDPWD, after a `cd` — often name the data root. A shell the
# agent starts sets them afresh for its own directory, but the claude process itself, and
# any MCP server it starts, keeps what it inherits. They are stripped with the FATHOM_*
# variables; a child's shell sets them again from its own working directory.
HARNESS_DIR_VARS: frozenset[str] = frozenset({"PWD", "OLDPWD"})


def without_harness_vars(
    env: Mapping[str, str], *, hidden: Iterable[str | os.PathLike[str]] | None = None
) -> dict[str, str]:
    """A copy of *env* without fathom's own state.

    Drops every variable whose name starts with ``FATHOM_`` and the working-directory
    variables in :data:`HARNESS_DIR_VARS`, comparing names case-insensitively, and then
    withholds the hidden directories (:func:`withhold_hidden_dirs`): *hidden*, or, when
    it is ``None``, the ones registered with :func:`hidden_from_children`. Any child
    process that runs code fathom does not control should start from this.
    """
    named = {
        k: v
        for k, v in env.items()
        if not (k.upper().startswith(HARNESS_ENV_PREFIX) or k.upper() in HARNESS_DIR_VARS)
    }
    return withhold_hidden_dirs(named, hidden=hidden)


# Directories a child must not learn the location of: the data root, while a command
# runs against it (the CLI registers it with `hidden_from_children`). Stripping by name
# does not cover a variable that names one by VALUE: when fathom runs from a virtual
# environment inside the data root (`uv run fathom` in a data repository that pins it),
# VIRTUAL_ENV names that environment and PATH starts with its scripts directory.
_HIDDEN_DIRS: list[Path] = []


@contextlib.contextmanager
def hidden_from_children(*paths: str | os.PathLike[str]) -> Iterator[None]:
    """While the block runs, :func:`without_harness_vars` also withholds *paths*."""
    entries = [Path(os.path.abspath(p)) for p in paths]
    _HIDDEN_DIRS.extend(entries)
    try:
        yield
    finally:
        for entry in entries:
            with contextlib.suppress(ValueError):
                _HIDDEN_DIRS.remove(entry)


def hidden_dirs() -> tuple[Path, ...]:
    """The directories registered with :func:`hidden_from_children`, oldest first."""
    return tuple(_HIDDEN_DIRS)


def _comparable(text: str) -> str:
    """*text* with forward slashes, and lower-cased on Windows, where paths ignore case."""
    text = text.replace("\\", "/")
    return text.lower() if os.name == "nt" else text


def _dir_spellings(path: Path) -> set[str]:
    """Comparable spellings of *path*: as given and resolved, and on a drive, the form
    Git Bash and MSYS tools use (``/c/...``)."""
    forms: set[str] = set()
    candidates = [Path(os.path.abspath(path))]
    with contextlib.suppress(OSError):
        candidates.append(Path(path).resolve())
    for candidate in candidates:
        form = _comparable(str(candidate)).rstrip("/")
        if not form or Path(candidate).parent == Path(candidate):
            continue
        forms.add(form)
        drive = re.match(r"([A-Za-z]):/", form)
        if drive:
            forms.add(f"/{drive.group(1).lower()}/{form[3:]}")
    return forms


def _withholdable(path: Path) -> bool:
    """False for a directory that holds the home or the temporary directory.

    Every process is handed those through variables it cannot run without (HOME,
    USERPROFILE, TEMP, and the PATH entries under them), so such a directory cannot be
    withheld, and trying would break every child instead.
    """
    here = _dir_spellings(path)
    for needed in (Path.home(), Path(tempfile.gettempdir())):
        for form in _dir_spellings(needed):
            if any(form == h or form.startswith(h + "/") for h in here):
                return False
    return True


def withhold_hidden_dirs(
    env: Mapping[str, str], *, hidden: Iterable[str | os.PathLike[str]] | None = None
) -> dict[str, str]:
    """A copy of *env* that names none of the *hidden* directories.

    PATH keeps every entry that does not lie in one; any other variable whose value
    names one, anywhere in it, is dropped. *hidden* defaults to the directories
    registered with :func:`hidden_from_children`. A directory that holds the home or the
    temporary directory is left alone (:func:`_withholdable`).
    """
    dirs = [Path(p) for p in (hidden if hidden is not None else _HIDDEN_DIRS)]
    forms = sorted(
        {f for d in dirs if _withholdable(d) for f in _dir_spellings(d)}, key=len, reverse=True
    )
    if not forms:
        return dict(env)
    # A spelling followed by a separator, a list delimiter, a quote or the end: the
    # directory itself or a path in it, and not a sibling that shares a prefix with it.
    named = re.compile("(?:" + "|".join(re.escape(f) for f in forms) + r")(?=$|[/;:,\"'\s])")

    def _inside(entry: str) -> bool:
        entry = _comparable(entry.strip().strip('"')).rstrip("/")
        return any(entry == f or entry.startswith(f + "/") for f in forms)

    out: dict[str, str] = {}
    for name, value in env.items():
        if name.upper() == "PATH":
            out[name] = os.pathsep.join(e for e in value.split(os.pathsep) if not _inside(e))
        elif not named.search(_comparable(value)):
            out[name] = value
    return out


def env_for_agent_code(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """*env* (default: the host environment) as a process running the agent's code gets it.

    Without fathom's own state (:func:`without_harness_vars`) and without the billing and
    routing variables in :data:`_SPAWN_ENV_STRIP`, which include the API credentials.
    A spawn gets this plus its config dir (:func:`make_spawn_env`); a gate, which runs
    code the agent wrote and whose output goes back to the agent, gets it as it is, so
    nothing the spawn itself is denied reaches the agent's code by that route.
    """
    out = without_harness_vars(os.environ if env is None else env)
    for name in _SPAWN_ENV_STRIP:
        out.pop(name, None)
    return out


def make_spawn_env(config_dir: str) -> dict[str, str]:
    """Base environment for an isolated spawn.

    The host environment minus the billing/routing diverters in
    :data:`_SPAWN_ENV_STRIP` and minus fathom's own state (every ``FATHOM_*``
    variable, the working-directory variables, and any value naming a hidden
    directory such as the data root, :func:`without_harness_vars`), which is
    :func:`env_for_agent_code`, with ``CLAUDE_CONFIG_DIR`` pinned to the
    credential-only temp dir.  Both spawn
    paths — the single-spawn adapter and the series engine — build their env here,
    so neither can be rerouted off the copied subscription credential by a stray
    host variable, and neither hands the agent fathom's own state.  The host
    environment itself is not modified: fathom still reads its variables in its own
    process.

    A scenario's ``[env]`` is applied on top of this by :func:`_apply_env_template`.
    """
    env = env_for_agent_code()
    env["CLAUDE_CONFIG_DIR"] = config_dir
    return env


# ---------------------------------------------------------------------------
# Stream parsing — defensive NDJSON, with partial-stream tolerance
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _Parsed:
    """Economy + outcome fields recovered from one spawn's output."""

    result_text: str = ""
    cost_usd: float = 0.0
    num_turns: int = 0
    is_error: bool = False
    usage: dict[str, Any] = dataclasses.field(default_factory=dict)
    model_id: str = ""
    cli_version: str = ""
    duration_ms: float = 0.0
    saw_result: bool = False


def parse_stream(lines: Iterable[str]) -> _Parsed:
    """Parse ``--output-format stream-json`` NDJSON, defensively.

    Tolerates a stream cut off mid-line (the JSON fragment a timeout kill leaves
    behind is skipped).  When the stream ends before the ``result`` event, usage
    and turn count are recovered from the last assistant message so a timed-out
    run still reports the economy it burned.
    """
    p = _Parsed()
    last_assistant_usage: dict[str, Any] = {}
    assistant_turns = 0
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue  # a stream cut off mid-line — tolerate it
        if not isinstance(obj, dict):
            continue
        kind = obj.get("type")
        if kind == "system" and obj.get("subtype") == "init":
            p.model_id = obj.get("model") or p.model_id
            version = obj.get("version")
            if isinstance(version, str) and version:
                p.cli_version = version
        elif kind == "result":
            p.saw_result = True
            p.result_text = obj.get("result") or p.result_text
            p.cost_usd = obj.get("total_cost_usd") or p.cost_usd
            p.num_turns = obj.get("num_turns") or p.num_turns
            p.is_error = bool(obj.get("is_error", p.is_error))
            if isinstance(obj.get("usage"), dict):
                p.usage = obj["usage"]
            duration = obj.get("duration_ms")
            if isinstance(duration, (int, float)):
                p.duration_ms = float(duration)
            model = obj.get("model")
            if isinstance(model, str) and model and not p.model_id:
                p.model_id = model
        elif kind == "assistant":
            msg = obj.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("usage"), dict):
                last_assistant_usage = msg["usage"]
                assistant_turns += 1
    if not p.saw_result:
        # Partial stream: recover what economy we can from assistant messages.
        p.usage = last_assistant_usage
        p.num_turns = assistant_turns
    return p


def parse_result_json(stdout: str) -> _Parsed:
    """Parse ``--output-format json`` (a single result object), defensively."""
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return _Parsed(result_text=stdout)
    if not isinstance(data, dict):
        return _Parsed(result_text=stdout)
    p = _Parsed(saw_result=True)
    p.result_text = data.get("result") or ""
    p.cost_usd = data.get("total_cost_usd") or 0.0
    p.num_turns = data.get("num_turns") or 0
    p.is_error = bool(data.get("is_error", False))
    if isinstance(data.get("usage"), dict):
        p.usage = data["usage"]
    duration = data.get("duration_ms")
    if isinstance(duration, (int, float)):
        p.duration_ms = float(duration)
    model = data.get("model")
    if isinstance(model, str):
        p.model_id = model
    return p


def _tokens(usage: Mapping[str, Any]) -> tuple[int, int, int]:
    """``(input, output, cache)`` token counts from a CLI usage mapping.

    Cache combines the read + creation buckets the CLI reports separately.
    """
    tin = int(usage.get("input_tokens") or 0)
    tout = int(usage.get("output_tokens") or 0)
    tcache = int(usage.get("cache_read_input_tokens") or 0) + int(
        usage.get("cache_creation_input_tokens") or 0
    )
    return tin, tout, tcache


# A per-family price table once backed a fallback for cases where the CLI reported
# zero cost. That case no longer occurs under subscription auth. What takes its place
# is not another estimate: an absent cost is REPORTED as absent (``cost_source``),
# because a plausible number wearing no label is worse than a gap that says so — the
# whole point of the economy axis.

COST_SOURCE_REPORTED = "reported"
COST_SOURCE_NONE = "none"


def cost_and_source(cost_usd: float, tokens_in: int, tokens_out: int) -> tuple[float, str]:
    """``(cost, source)`` for one spawn, never inventing a number.

    A spawn that consumed no tokens genuinely cost nothing, so zero there is
    ``reported``. A spawn that consumed tokens and reports zero is a GAP: the source
    says so and the caller warns, instead of a price table filling it in and every
    downstream sum reading as measured.
    """
    if cost_usd:
        return cost_usd, COST_SOURCE_REPORTED
    if tokens_in or tokens_out:
        return 0.0, COST_SOURCE_NONE
    return 0.0, COST_SOURCE_REPORTED


def _classify_infrastructure(text: str) -> bool:
    """True when ``text`` carries an auth or subscription usage-limit signature.

    Used by the series strategy to classify engine tracker events. The single-spawn
    adapter path uses :func:`_spawn_is_infrastructure`, which adds the success nuance.
    """
    return bool(_AUTH.search(text) or _USAGE_LIMIT.search(text))


def _spawn_is_infrastructure(stderr: str, result_text: str, *, success: bool) -> bool:
    """Adapter-path classification for a single spawn (auth / usage-limit).

    The CLI reports its OWN infrastructure failures — auth expiry, subscription cap —
    on stderr, or via a non-success result (nonzero exit / ``is_error``). A cleanly
    SUCCESSFUL spawn (``success=True``) completed the task, so any auth / quota /
    usage-limit phrasing in its OUTPUT is task content: an error handler the agent
    wrote, a test named ``test_quota_exceeded``, a CLI hint like "Upgrade to Pro", a
    data source reporting it needs an auth profile. Treating that as infrastructure
    discards a good trial, halts the matrix, and re-burns money on resume — so neither
    signature counts as infrastructure on a successful spawn's result text.

    Both signatures therefore key on the SAME rule: infrastructure iff the signature is
    on the CLI's own stderr, OR the spawn did not cleanly succeed. (Real caps/auth
    refusals carry ``is_error`` / a nonzero exit, so ``success`` is already False for
    them — e.g. the subscription usage-limit result event sets ``is_error: true``.)
    """
    if _USAGE_LIMIT.search(stderr or "") or _AUTH.search(stderr or ""):
        return True
    return bool(
        not success and (_USAGE_LIMIT.search(result_text or "") or _AUTH.search(result_text or ""))
    )


# ---------------------------------------------------------------------------
# Command assembly — pure (no I/O), headless default-deny
# ---------------------------------------------------------------------------


def build_command(
    *,
    model: str,
    effort: str,
    max_turns: int,
    max_budget_usd: float,
    allowed_tools: Sequence[str],
    disallowed_tools: Sequence[str] = (),
    append_system_prompt_file: str | None = None,
    plugin_dirs: Sequence[str] = (),
    stream: bool = True,
) -> list[str]:
    """Assemble the ``claude -p`` argv.  Pure — no I/O.

    No ``--bare`` (it strips the config-bound subscription login); isolation
    comes from the clean ``CLAUDE_CONFIG_DIR`` passed to the spawn.  No
    ``--permission-mode`` and no ``--dangerously-skip-permissions``: bypass
    auto-approves every tool and turns ``--allowed-tools`` into decoration —
    headless default-deny plus the explicit allowlist is the real boundary, with
    ``--disallowed-tools`` as belt-and-braces.  ``--effort`` gives cross-arm
    parity with the engine (which always passes it; spec §5).
    """
    cmd = [
        "claude",
        "-p",
        "--no-session-persistence",
        "--model",
        model,
        "--effort",
        effort,
        "--max-turns",
        str(max_turns),
        "--allowed-tools",
        ",".join(allowed_tools),
    ]
    if disallowed_tools:
        cmd += ["--disallowed-tools", ",".join(disallowed_tools)]
    if append_system_prompt_file:
        cmd += ["--append-system-prompt-file", append_system_prompt_file]
    for plugin_dir in plugin_dirs:
        cmd += ["--plugin-dir", plugin_dir]
    # `is not None`, not truthiness: a cap of 0 means "spend nothing on this spawn", and
    # truthiness silently dropped it — so the single most restrictive cap an operator can
    # ask for was the one value that fell back to the adapter's $5 default.
    if max_budget_usd is not None:
        cmd += ["--max-budget-usd", str(max_budget_usd)]
    cmd += (
        ["--output-format", "stream-json", "--verbose"] if stream else ["--output-format", "json"]
    )
    return cmd


# ---------------------------------------------------------------------------
# Injectable subprocess boundary
# ---------------------------------------------------------------------------


class Spawn(Protocol):
    """The subprocess boundary, injectable so tests run with a stub.

    Mirrors the slice of ``subprocess.run`` the adapter needs; an implementation
    returns a ``CompletedProcess`` or raises ``subprocess.TimeoutExpired`` /
    ``FileNotFoundError`` exactly as the stdlib does.
    """

    def __call__(
        self,
        argv: Sequence[str],
        *,
        input: str,
        timeout: float | None,
        env: Mapping[str, str],
        cwd: str | None,
    ) -> subprocess.CompletedProcess: ...


def terminate_process_tree(pid: int) -> None:
    """Terminate ``pid`` and all of its descendants.

    The claude CLI spawns tool subprocesses as its own children; killing only the
    direct child (as ``subprocess.run``'s timeout does) orphans those grandchildren
    to keep mutating the workspace the verifier is about to score. Windows:
    ``taskkill /T`` walks the child tree. POSIX: the child is started in its own
    session, so ``killpg`` reaches the group. Shared by the adapter spawn and the
    series engine boundary (one home, no drift).
    """
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
    else:
        import signal

        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(os.getpgid(pid), signal.SIGKILL)


def pid_alive(pid: int) -> bool:
    """True if ``pid`` is a live process (used by the timeout no-orphan checks)."""
    if os.name == "nt":
        proc = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in (proc.stdout or "")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _subprocess_spawn(
    argv: Sequence[str],
    *,
    input: str,
    timeout: float | None,
    env: Mapping[str, str],
    cwd: str | None,
) -> subprocess.CompletedProcess:
    """Default boundary: Popen the CLI, killing the whole process tree on timeout.

    ``subprocess.run``'s timeout kills only the direct child, so the CLI's tool
    grandchildren are orphaned — they keep mutating the scored workspace, and an
    inherited stdout pipe can block the harness past the timeout. Popen plus a
    process-tree kill terminates them, mirroring the engine boundary (spec §6).
    Still re-raises ``TimeoutExpired`` (carrying whatever streamed before the kill)
    so the adapter's timeout path can recover the economy the run burned.
    """
    popen_kwargs: dict[str, Any] = {}
    if os.name != "nt":
        # Own session/group so a timeout can killpg the CLI and its tool children.
        popen_kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        list(argv),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=dict(env),
        cwd=cwd,
        **popen_kwargs,
    )
    try:
        out, err = proc.communicate(input=input, timeout=timeout)
        return subprocess.CompletedProcess(list(argv), proc.returncode, out, err)
    except subprocess.TimeoutExpired:
        terminate_process_tree(proc.pid)
        try:
            out, err = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
        raise subprocess.TimeoutExpired(list(argv), timeout, output=out, stderr=err) from None


# How long a stopped command's output is drained. Only a process that left the tree
# (one that detached itself) can hold the pipes past the stop.
_SHELL_DRAIN_S = 10.0


def _stop_shell_tree(proc: subprocess.Popen) -> None:
    """Stop the shell *proc* and every process under it."""
    if os.name == "nt":
        terminate_process_tree(proc.pid)
        return
    import signal

    # The shell leads a session of its own (``start_new_session``), so its group id is
    # its pid, still valid when the shell itself has already exited.
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(proc.pid, signal.SIGKILL)


def _drain_stopped(proc: subprocess.Popen) -> tuple[str, str]:
    """What a stopped command printed, waiting at most :data:`_SHELL_DRAIN_S`."""
    try:
        out, err = proc.communicate(timeout=_SHELL_DRAIN_S)
    except subprocess.TimeoutExpired:
        # Something outside the tree holds the pipes; stop waiting for it.
        with contextlib.suppress(OSError):
            proc.kill()
        if os.name != "nt":
            for stream in (proc.stdout, proc.stderr):
                with contextlib.suppress(OSError):
                    if stream is not None:
                        stream.close()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=_SHELL_DRAIN_S)
        return "", ""
    return out or "", err or ""


def run_shell_bounded(
    cmd: str,
    *,
    cwd: str | os.PathLike[str],
    env: Mapping[str, str],
    timeout: float,
    encoding: str | None = "utf-8",
) -> subprocess.CompletedProcess:
    """Run *cmd* through the shell; stop its whole process tree if it outlives *timeout*.

    The runner for gate commands. ``subprocess.run``'s timeout kills the shell alone: on
    Windows it then waits for every process still holding the output pipes, so a hung
    test under the gate holds the matrix until it finishes; on POSIX it returns at once
    and the shell's children run on, orphaned, writing into a workspace the caller has
    already cleaned and the verifier is about to score. Here, on a timeout, the tree
    (:func:`terminate_process_tree`; on POSIX, the session the shell leads) is stopped
    before the output is drained, and ``TimeoutExpired`` is raised, carrying what was
    read, only once it is gone. Any other exception that interrupts the wait
    (``KeyboardInterrupt``) stops the tree too, as ``subprocess.run`` stops its child.

    Returns a ``CompletedProcess`` as ``subprocess.run`` would, with text decoded as
    *encoding* (``None``: the locale's) and undecodable bytes replaced. A stream a reader
    thread failed to decode is ``None``, as there. The shell inherits stdin.
    """
    popen_kwargs: dict[str, Any] = {}
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    # cmd is a bank- or scenario-authored gate command; shell syntax is the point.
    proc = subprocess.Popen(  # noqa: S602
        cmd,
        shell=True,
        cwd=str(cwd),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding=encoding,
        errors="replace",
        **popen_kwargs,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _stop_shell_tree(proc)
        out, err = _drain_stopped(proc)
        raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err) from None
    except BaseException:
        _stop_shell_tree(proc)
        with contextlib.suppress(OSError):
            proc.kill()
        raise
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


# ---------------------------------------------------------------------------
# Per-scenario environment injection ([env] table — non-secret config only)
# ---------------------------------------------------------------------------

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _apply_env_template(
    env: dict[str, str], template: Sequence[tuple[str, str]], *, workspace: str
) -> dict[str, str]:
    """Apply per-scenario ``[env]`` overrides to a copy of *env*.

    Substitutes ``${workspace}`` -> *workspace* and ``${VAR}`` -> the inherited
    value of VAR (empty if unset), reading from the pre-override *env* so a
    PATH-prepend like ``<dir>;${PATH}`` works.  Non-secret config only.

    *env* is the spawn env from :func:`make_spawn_env`, so the overrides land after
    the ``FATHOM_*`` strip.  A scenario may set any name, a ``FATHOM_*`` one included
    (say, ``FATHOM_HOME`` pointing into the workspace for an arm that evaluates a tool
    which reads it): the value is written in the arm file and its template enters
    ``config_hash``, so it is a declared treatment rather than a leak.  What a scenario
    cannot do is forward the host's value — ``${FATHOM_HOME}`` (or ``${PWD}``) reads
    the stripped env and substitutes as empty.
    """
    out = dict(env)
    for key, value_template in template:
        out[key] = _subst_env(value_template, env, workspace)
    return out


def _subst_env(template: str, env: Mapping[str, str], workspace: str) -> str:
    def _repl(m: re.Match[str]) -> str:
        name = m.group(1)
        return workspace if name == "workspace" else env.get(name, "")

    return _ENV_VAR_RE.sub(_repl, template)


# ---------------------------------------------------------------------------
# The Runner adapter
# ---------------------------------------------------------------------------


class ClaudeCliRunner:
    """Subscription Claude CLI Runner (ADR-0001 / ADR-0004).

    The allow/disallow tool lists are adapter configuration, not scenario
    fields: ``ResolvedScenario`` carries ``model``/``effort``/``limits``
    but no per-tool lists, and default-deny is an adapter-level isolation
    property (ADR-0004).  A strategy executor supplies the lists per arm.
    Per-spawn ``--max-turns`` / ``--max-budget-usd`` likewise default here and
    are overridden per task by the executor.

    ``stage_files`` copies the ``[context]`` body and the ``[plugins]`` mounts into a
    directory of each spawn's own and passes the copies in the argv
    (:func:`stage_arm_files`), so the agent cannot learn where the declared files, and
    so the data root, are. A trial's runner turns it on (``fathom run``); it is off by
    default, and the attributes keep the declared paths either way.
    """

    def __init__(
        self,
        *,
        allowed_tools: Sequence[str] = (),
        disallowed_tools: Sequence[str] = (),
        append_system_prompt_file: str | None = None,
        plugin_dirs: Sequence[str] = (),
        stage_files: bool = False,
        settings_file: str | None = None,
        real_config_dir: str | None = None,
        max_attempts: int = 3,
        default_max_turns: int = 30,
        default_max_budget_usd: float = 5.0,
        default_timeout_s: float = 1800.0,
        stream: bool = True,
        cli_version: str = "",
        spawn: Spawn = _subprocess_spawn,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.allowed_tools = tuple(allowed_tools)
        self.disallowed_tools = tuple(disallowed_tools)
        self.append_system_prompt_file = append_system_prompt_file
        self.plugin_dirs = tuple(plugin_dirs)
        self.stage_files = stage_files
        self.settings_file = settings_file
        self.real_config_dir = real_config_dir
        self.max_attempts = max_attempts
        self.default_max_turns = default_max_turns
        self.default_max_budget_usd = default_max_budget_usd
        self.default_timeout_s = default_timeout_s
        self.stream = stream
        self.cli_version = cli_version
        self._spawn = spawn
        self._sleep = sleep
        self._clock = clock

    # -- Runner protocol ----------------------------------------------------

    def execute(
        self,
        prompt: str,
        workspace: Path,
        scenario: ResolvedScenario,
        max_turns: int | None = None,
    ) -> RunRecord:
        """Run ``prompt`` in ``workspace`` under ``scenario``; return a RunRecord.

        Builds the credential-only temp config (and, with ``stage_files``, the copies
        of the arm's files), runs with the retry/classify loop, and always tears both
        down.  ``max_turns`` overrides the adapter default for this spawn (the trial's
        turn budget); ``None`` keeps the default.

        A copy of the arm's files that fails is an infrastructure error: spawning
        without them would run the treatment arm as the control.
        """
        timeout = scenario.limits.trial_timeout_s or self.default_timeout_s
        turns = max_turns if max_turns else self.default_max_turns
        config_dir = make_isolated_config(self.real_config_dir, settings_file=self.settings_file)
        stage_dir: str | None = None
        try:
            inject, mounts = self.append_system_prompt_file, self.plugin_dirs
            if self.stage_files and (inject or mounts):
                stage_dir = tempfile.mkdtemp(prefix="fathom_stage_")
                try:
                    inject, mounts = stage_arm_files(
                        Path(stage_dir), inject=inject, plugin_dirs=mounts
                    )
                except OSError as exc:
                    return RunRecord(
                        status=ExitStatus.INFRASTRUCTURE,
                        result_text=(
                            "could not copy the arm's [context]/[plugins] files for the "
                            f"spawn: {type(exc).__name__}: {exc}"
                        )[:500],
                        cli_version=self.cli_version,
                    )
            return self._run(
                prompt,
                str(workspace),
                scenario.model,
                scenario.effort,
                timeout,
                config_dir,
                turns,
                env_template=scenario.env.vars,
                append_system_prompt_file=inject,
                plugin_dirs=mounts,
            )
        finally:
            cleanup_dir(config_dir)
            if stage_dir is not None:
                cleanup_dir(stage_dir)

    # -- internals ----------------------------------------------------------

    def _run(
        self,
        prompt: str,
        cwd: str,
        model: str,
        effort: str,
        timeout: float,
        config_dir: str,
        max_turns: int,
        env_template: Sequence[tuple[str, str]] = (),
        append_system_prompt_file: str | None = None,
        plugin_dirs: Sequence[str] = (),
    ) -> RunRecord:
        cmd = build_command(
            model=model,
            effort=effort,
            max_turns=max_turns,
            max_budget_usd=self.default_max_budget_usd,
            allowed_tools=self.allowed_tools,
            disallowed_tools=self.disallowed_tools,
            append_system_prompt_file=append_system_prompt_file,
            plugin_dirs=plugin_dirs,
            stream=self.stream,
        )
        env = make_spawn_env(config_dir)
        if env_template:
            env = _apply_env_template(env, env_template, workspace=cwd)
        start = self._clock()
        last: tuple[subprocess.CompletedProcess, _Parsed] | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                proc = self._spawn(cmd, input=prompt, timeout=timeout, env=env, cwd=cwd)
            except subprocess.TimeoutExpired as exc:
                return self._timeout_record(exc, timeout, start)
            except FileNotFoundError:
                return RunRecord(
                    status=ExitStatus.INFRASTRUCTURE,
                    result_text="claude CLI not found on PATH",
                    cli_version=self.cli_version,
                )
            self._tee_stream(proc.stdout or "", attempt)
            parsed = self._parse(proc.stdout or "")
            success = proc.returncode == 0 and not parsed.is_error
            # Infrastructure (never scored, never retried). A usage-limit/quota signature is
            # never legitimate task content, so it is infrastructure wherever it appears; an
            # auth signature CAN be task content (an env-setup task reporting a profile needs
            # auth), so it is infrastructure only on the CLI's OWN stderr, or when the spawn
            # did not cleanly succeed — a SUCCESSFUL task that merely reports auth status is
            # scored, not misread as a spawn auth failure.
            if _spawn_is_infrastructure(
                proc.stderr or "", parsed.result_text or "", success=success
            ):
                return self._build_record(parsed, start, ExitStatus.INFRASTRUCTURE, proc.stderr)
            if success:
                return self._build_record(parsed, start, ExitStatus.OK, proc.stderr)
            last = (proc, parsed)
            if attempt < self.max_attempts and _TRANSIENT.search(proc.stderr or ""):
                # Exponential backoff with jitter, as in the original.
                self._sleep(min(10 * 2 ** (attempt - 1), 120) + random.uniform(0, 5))
                continue
            break
        if last is None:
            return RunRecord(status=ExitStatus.ERROR, cli_version=self.cli_version)
        proc, parsed = last
        return self._build_record(parsed, start, ExitStatus.ERROR, proc.stderr)

    def _parse(self, stdout: str) -> _Parsed:
        return parse_stream(stdout.splitlines()) if self.stream else parse_result_json(stdout)

    @staticmethod
    def _tee_stream(stdout: str, attempt: int) -> None:
        """Persist the raw spawn stdout when FATHOM_STREAM_DIR is set (opt-in).

        The parsed RunRecord keeps only economy/result fields; post-hoc analyses
        (tool-invocation counts, skill-activation measurement) need the raw
        stream events, which are otherwise discarded. FATHOM_STREAM_TAG (set by
        the run loop per trial) names the file. Both are read here, in fathom's own
        process; the spawn's env never carries them (:func:`make_spawn_env`).
        Best-effort: a persistence failure must never affect the trial.
        """
        stream_dir = os.environ.get("FATHOM_STREAM_DIR")
        if not stream_dir or not stdout:
            return
        try:
            tag = os.environ.get("FATHOM_STREAM_TAG", "untagged")
            safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in tag)
            out = Path(stream_dir)
            out.mkdir(parents=True, exist_ok=True)
            name = f"{safe}--a{attempt}--{int(time.time() * 1000)}.ndjson"
            (out / name).write_text(stdout, encoding="utf-8")
        except OSError:
            pass

    def _build_record(
        self,
        parsed: _Parsed,
        start: float,
        status: ExitStatus,
        fallback_stderr: str | None = "",
    ) -> RunRecord:
        tin, tout, tcache = _tokens(parsed.usage)
        duration_s = parsed.duration_ms / 1000.0 if parsed.duration_ms else (self._clock() - start)
        result_text = parsed.result_text or (fallback_stderr or "")[:500]
        cost_usd_est, cost_source = cost_and_source(parsed.cost_usd, tin, tout)
        if cost_source == COST_SOURCE_NONE:
            warnings.warn(
                f"no cost reported for a spawn that consumed {tin} in / {tout} out tokens "
                f"on {parsed.model_id or 'an unnamed model'}; recorded as "
                "cost_source=none rather than estimated from a local price table",
                stacklevel=2,
            )
        return RunRecord(
            status=status,
            tokens_in=tin,
            tokens_out=tout,
            tokens_cache=tcache,
            num_turns=parsed.num_turns,
            duration_s=duration_s,
            cost_usd_est=cost_usd_est,
            cost_source=cost_source,
            model_id=parsed.model_id,
            cli_version=parsed.cli_version or self.cli_version,
            result_text=result_text,
            usage=dict(parsed.usage),
        )

    def _timeout_record(
        self,
        exc: subprocess.TimeoutExpired,
        timeout: float,
        start: float,
    ) -> RunRecord:
        # Parse whatever streamed before the kill: economy spent pre-timeout must
        # still count, or the report silently undercounts.
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        parsed = self._parse(out) if out.strip() else _Parsed()
        rec = self._build_record(parsed, start, ExitStatus.TIMEOUT)
        # A partial stream has no result event, so prefer the known timeout value.
        rec.duration_s = parsed.duration_ms / 1000.0 if parsed.duration_ms else float(timeout)
        rec.result_text = (rec.result_text + f"\n[TIMEOUT after {timeout}s]").strip()
        return rec
