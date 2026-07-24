"""Subscription Claude CLI adapter — vendored spawn core.

Vendored from craft-collection's ``evals/harness/claude_runner.py`` per
``docs/adr/0004-vendor-claude-runner-core.md``: the proven, debugged spawn
mechanics are *copied*, not depended on (craft-collection is itself a fathom test
subject), and refactored behind the ``Runner`` protocol (ADR-0001).  The hard-won
isolation properties are preserved:

* a temp ``CLAUDE_CONFIG_DIR`` holding only the copied credential — no CLAUDE.md,
  settings.json, or history leaks user context into the supposedly clean arms;
* headless **default-deny**: the command carries no ``--permission-mode`` and no
  ``--dangerously-skip-permissions`` (``bypassPermissions`` auto-approves every
  tool and nullifies the allowlist — it is how a spawn once wrote into a real
  repo); the explicit allow/disallow lists are the actual boundary;
* ``--output-format stream-json`` parsing that tolerates a stream cut off
  mid-line on timeout;
* retry with a cap on transient (server/network) failures only.

Divergence from upstream is expected and managed deliberately (a
reflection-triage input, not an automatic sync).  Adaptations to fit the
protocol: the skill-activation / written-text extraction is dropped (the trigger
axis is a v1 non-goal); a ``--effort`` flag is added (cross-arm parity, spec §5);
auth and subscription usage-limit responses are classified as **infrastructure**
errors so they never score and never burn a trial's error-retry budget; and a
partial stream recovers what economy it can from assistant messages.

Stdlib only.  The subprocess boundary is injectable so every test runs with a
stub — no real spawns here (that is the smoke gate's job, spec §11).
"""

from __future__ import annotations

import dataclasses
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
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
    # The CLI's 5-hour rolling-window message ("You've hit your session limit --
    # resets 11:10pm"): without this the refusal scores as an ERRORED trial and
    # the matrix keeps burning cells (observed 2026-07-01, ~30 poisoned trials).
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
            try:
                shutil.copy2(src, dest / name)
            except OSError:
                pass  # locked/unreadable; the smoke gate catches a dead config
    if settings_file:
        try:
            shutil.copy2(settings_file, dest / "settings.json")
        except OSError:
            pass  # missing/unreadable; the factory warns and the arm degrades to control
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


def make_spawn_env(config_dir: str) -> dict[str, str]:
    """Base environment for an isolated spawn.

    The host environment minus the billing/routing diverters in
    :data:`_SPAWN_ENV_STRIP`, with ``CLAUDE_CONFIG_DIR`` pinned to the
    credential-only temp dir.  Both spawn paths — the single-spawn adapter and the
    series engine — build their env here, so neither can be silently rerouted off
    the copied subscription credential by a stray host variable.
    """
    env = os.environ.copy()
    for name in _SPAWN_ENV_STRIP:
        env.pop(name, None)
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


# Per-1k-token (input, output) USD prices by model family, from the canonical
# model-tier rates (haiku=weak, sonnet=mid, opus=strong, fable=frontier).
# Used ONLY as a fallback when the CLI reports ``total_cost_usd == 0`` — the
# subscription-auth case behind defect D2.  The CLI's own ``total_cost_usd`` is
# always preferred when present (it also prices cache reads/writes, which this
# input+output approximation deliberately omits for lack of a published rate).
_PRICE_PER_1K: dict[str, tuple[float, float]] = {
    "haiku": (0.001, 0.005),
    "sonnet": (0.003, 0.015),
    "opus": (0.005, 0.025),
    "fable": (0.010, 0.050),
}
# Unknown/empty model id → strong (opus), fathom's default model: a conservative
# non-zero estimate beats silently reporting $0.
_DEFAULT_PRICE = _PRICE_PER_1K["opus"]


def estimate_cost_usd(model_id: str, tokens_in: int, tokens_out: int) -> float:
    """Token×price USD estimate (canonical model-tier rates).

    Resolves the per-1k input/output price from the model family named in
    ``model_id`` (substring match, robust to dated snapshots like
    ``claude-opus-4-8-20260115``); an unrecognized id falls back to the strong
    (opus) rate.  Returns 0.0 for zero tokens.
    """
    lower = model_id.lower()
    rate_in, rate_out = _DEFAULT_PRICE
    for family, rate in _PRICE_PER_1K.items():
        if family in lower:
            rate_in, rate_out = rate
            break
    return tokens_in / 1000 * rate_in + tokens_out / 1000 * rate_out


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
    if not success and (_USAGE_LIMIT.search(result_text or "") or _AUTH.search(result_text or "")):
        return True
    return False


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
    if max_budget_usd:
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
        subprocess.run(  # noqa: S603, S607 - fixed argv, no shell
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
    else:
        import signal

        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def pid_alive(pid: int) -> bool:
    """True if ``pid`` is a live process (used by the timeout no-orphan checks)."""
    if os.name == "nt":
        proc = subprocess.run(  # noqa: S603, S607 - fixed argv, no shell
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
    proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
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
    fields: PR04's ``ResolvedScenario`` carries ``model``/``effort``/``limits``
    but no per-tool lists, and default-deny is an adapter-level isolation
    property (ADR-0004).  A strategy executor supplies the lists per arm.
    Per-spawn ``--max-turns`` / ``--max-budget-usd`` likewise default here and
    are overridden per task by the executor.
    """

    def __init__(
        self,
        *,
        allowed_tools: Sequence[str] = (),
        disallowed_tools: Sequence[str] = (),
        append_system_prompt_file: str | None = None,
        plugin_dirs: Sequence[str] = (),
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

        Builds the credential-only temp config, runs with the retry/classify
        loop, and always tears the temp config down.  ``max_turns`` overrides the
        adapter default for this spawn (the trial's turn budget); ``None`` keeps
        the default.
        """
        timeout = scenario.limits.trial_timeout_s or self.default_timeout_s
        turns = max_turns if max_turns else self.default_max_turns
        config_dir = make_isolated_config(self.real_config_dir, settings_file=self.settings_file)
        try:
            return self._run(
                prompt,
                str(workspace),
                scenario.model,
                scenario.effort,
                timeout,
                config_dir,
                turns,
                env_template=scenario.env.vars,
            )
        finally:
            cleanup_dir(config_dir)

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
    ) -> RunRecord:
        cmd = build_command(
            model=model,
            effort=effort,
            max_turns=max_turns,
            max_budget_usd=self.default_max_budget_usd,
            allowed_tools=self.allowed_tools,
            disallowed_tools=self.disallowed_tools,
            append_system_prompt_file=self.append_system_prompt_file,
            plugin_dirs=self.plugin_dirs,
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
                # Exponential backoff with jitter, exactly as upstream.
                self._sleep(min(10 * 2 ** (attempt - 1), 120) + random.uniform(0, 5))  # noqa: S311
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
        the run loop per trial) names the file. Best-effort: a persistence
        failure must never affect the trial.
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
        # Prefer the CLI's reported cost; fall back to a token×price estimate when
        # it is 0 (subscription auth reports total_cost_usd == 0 — defect D2).
        cost_usd_est = parsed.cost_usd or estimate_cost_usd(parsed.model_id, tin, tout)
        return RunRecord(
            status=status,
            tokens_in=tin,
            tokens_out=tout,
            tokens_cache=tcache,
            num_turns=parsed.num_turns,
            duration_s=duration_s,
            cost_usd_est=cost_usd_est,
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
