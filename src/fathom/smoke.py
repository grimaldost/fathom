"""Real-spawn isolation smoke gate (spec §11) — ``fathom smoke``.

The go/no-go gate that must pass before any paid matrix run **and again at every
resume** (spec §13): it asserts, on *real* spawns, the isolation properties the
rest of the harness assumes but that only a live spawn can prove.  Six assertion
groups, ported from craft-collection's ``evals/harness/smoke.py`` and extended
for fathom's engine boundary and plugin-mount fidelity:

0. **The credential is live.**  Free, spawns nothing, and runs FIRST because every
   group below it depends on a spawn that can authenticate.  Reads exactly two
   integers out of ``~/.claude/.credentials.json`` — ``expiresAt`` and
   ``refreshTokenExpiresAt`` — and never a token (ADR-0004: the credential is
   copied, not read).
1. **Credential-only spawn authenticates and completes.**  The temp
   ``CLAUDE_CONFIG_DIR`` holds exactly ``.credentials.json`` (no CLAUDE.md /
   settings.json / history leak — ADR-0004), and a tiny spawn under it is
   authenticated and returns ``OK`` (not an auth/usage-limit infrastructure
   error).
2. **A disallowed tool call is refused under default-deny.**  A read-only
   allowlist + explicit disallow means a spawn told to write a file creates
   none — the boundary ``bypassPermissions`` used to nullify (ADR-0004).
3. **Stream parsing detects activity.**  The vendored stream-json parser
   recovers turns/tokens from the real stream of group 1's spawn.
4. **Plugin mount/available (spec §5).**  A canary plugin is mounted via
   ``--plugin-dir``; the spawn's init event must list the canary skill in its
   ``skills`` array (treatment).  A control spawn without the mount must not list
   it.  Proves ``--plugin-dir`` wiring reaches the live CLI init layer — mount
   fidelity, not auto-fire (ADR-0006).
5. **Concurrency exclusion.**  Free and spawn-free: while one ticket holds a bank's
   run lock a second acquirer does not, and a ticket past the staleness horizon is
   released rather than honoured.  FATH-B64's corrected sequencing is that an
   operational check ships in the same change as its mechanism — a gate written after
   the thing it gates is a gate written to pass.
6. **Engine boundary: the §6-pinned non-bypass permission mode reaches the
   engine's spawned CLI invocation.**  A minimal one-PR series run against
   a scratch workspace, with ``claude`` shadowed by a PATH shim that records its
   argv (and spends **no** model tokens), confirms the engine spawns ``claude``
   with ``--permission-mode default`` and never ``--dangerously-skip-permissions``
   / ``bypassPermissions`` — the pinned non-bypass mode the §6 executor guarantees.

Exit nonzero on any violation; ``--force-fail`` appends a failing check to
demonstrate the nonzero path.

**A check that could not be proven is not a pass.**  Two of the assertions below
(activity detection, tool denial) read a *live* spawn's behaviour, and both used to
conclude from a spawn that never authenticated: "stream parsing detects activity"
passed on ``turns=1 tokens_in=0 tokens_out=0``, and "disallowed tool refused"
passed with no tool call to refuse.  They are now gated on liveness and report
``SKIPPED`` instead, and a SKIPPED check keeps the gate red — this is the go/no-go
before paid spend, so "we could not prove it" must never read as "go".

The design splits **pure assertions** (observation → :class:`SmokeResult`) from
the **probes** that perform the real I/O.  The assertions and the
:func:`run_smoke` plumbing are unit-tested with stub probes
(``tests/test_smoke_logic.py``, stdlib-runnable); the real-spawn path is
exercised manually via ``fathom smoke`` (no third-party imports here either —
stdlib only, plus the vendored adapter / series executor).
"""

from __future__ import annotations

import dataclasses
import io
import json
import os
import platform
import sys
import tempfile
import time
import zipfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TextIO

from fathom.adapters.base import ExitStatus
from fathom.adapters.claude_cli import ClaudeCliRunner, cleanup_dir, make_isolated_config
from fathom.scenario import LimitsOverride, ResolvedScenario, ToolsConfig
from fathom.strategies.series import NON_BYPASS_PERMISSION_MODE

if TYPE_CHECKING:
    from fathom.adapters.base import RunRecord

# Cheap, fast defaults for the real spawns — the smoke gate proves isolation, not
# capability, so it uses a small model, low effort, few turns, and a low budget.
DEFAULT_SMOKE_MODEL = "claude-haiku-4-5"
DEFAULT_SMOKE_EFFORT = "low"
DEFAULT_SPAWN_TIMEOUT_S = 180.0
# The engine boundary uses a token-free shim, so its wall-clock is only the
# `uv run` + engine startup; a few minutes bounds a hang without truncating it.
DEFAULT_ENGINE_TIMEOUT_S = 420.0

# The bypass surfaces the engine boundary must never see in a spawned argv.
_BYPASS_FLAG = "--dangerously-skip-permissions"
_BYPASS_MODE = "bypassPermissions"

# A short, distinctive token the K7 injection probe directs the model to emit via an
# injected system prompt — proof the --append-system-prompt-file body actually reaches
# and influences generation, i.e. the treatment arm is genuinely armed. An arm that
# spawns un-injected silently scores as the control and invalidates the comparison
# (cf. the matrix-run-1 unarmed-arms defect), so this is asserted on a real spawn.
INJECTION_CANARY = "ZQ7CANARY9X"

# Path to the tiny canary plugin used in the mount/available smoke check (spec §5).
# Lives under tests/fixtures/ so it travels with the repo but never becomes a
# dependency of the installed package.
_REPO_ROOT = Path(__file__).parent.parent.parent
CANARY_PLUGIN_DIR: Path = _REPO_ROOT / "tests" / "fixtures" / "canary-plugin"

# The skill identifier the canary plugin registers in the init event's ``skills``
# array.  Format: ``<plugin-name>:<skill-dir>``, matching the convention confirmed
# in the spike (humblepowers skills list as ``humblepowers:<skill-dir>``).
CANARY_SKILL = "fathom-smoke-canary:probe"

# How much credential life the gate requires before it says "go".  This is a FLOOR,
# not an estimate of matrix duration: smoke does not know how long a matrix will run,
# and pretending otherwise would be a number that looks like a forecast and is not.
# Thirty minutes is long enough that a green gate is not immediately followed by an
# auth failure mid-trial, and short enough that it refuses no legitimate run.
CREDENTIAL_MIN_TTL_S = 1800.0

# The only two fields the pre-flight reads.  Named as constants so a reviewer can see
# the whole of what leaves the credential file in one place (ADR-0004).
_CRED_BLOCK = "claudeAiOauth"
_CRED_EXPIRES_AT = "expiresAt"
_CRED_REFRESH_EXPIRES_AT = "refreshTokenExpiresAt"

# Minimal one-PR series template for the engine-boundary scratch run.  Structure
# mirrors the committed bank templates (§12); the §6 executor overwrites
# model/effort/permission_mode/budgets and strips `tier`, so the [governance]
# values here are placeholders.  The blocking gate is a trivial always-pass command
# so the engine's baseline gate stays green on the scratch fixture (§12: the
# deliberately-failing acceptance lives in a verifier, never in a gate).
_SMOKE_SERIES_TEMPLATE = """\
[series]
id = "fathom-smoke"
version = "1"

[branches]
base = "main"
integration = "fathom-smoke/integration"

[paths]
prompts = "prompts"
outputs = "outputs"

[governance]
model = "claude-haiku-4-5"
effort = "low"
permission_mode = "acceptEdits"
timeout_seconds = 120

[governance.budgets]
implementation = 1.0
review = 1.0
fix = 1.0

[governance.tools]
implementation = ["Read"]
review = ["Read"]
fix = ["Read"]

[review]
blocking = false
max_fix_attempts = 0

[[checks]]
name = "noop"
run = "python -c \\"pass\\""
blocking = true
independent = false

[[prs]]
id = "PR01"
branch = "fathom-smoke/pr01"
prompt = "PR01.md"
phase = "1"
depends_on = []
"""


@dataclasses.dataclass
class SmokeResult:
    """One assertion's verdict: a name, pass/fail, and a human-readable detail.

    ``ok`` means **proven true**, never "nothing contradicted it".  ``skipped``
    marks an assertion whose precondition did not hold — the spawn it reads never
    went live — and such a result carries ``ok=False``, so the gate cannot go green
    on a check that proved nothing.  The two states are reported separately because
    "this is broken" and "we could not tell" call for different actions.
    """

    name: str
    ok: bool
    detail: str = ""
    skipped: bool = False


def _skipped(name: str, detail: str) -> SmokeResult:
    """A check whose precondition did not hold: reported, never counted as a pass."""
    return SmokeResult(name, False, f"SKIPPED (spawn not live): {detail}", skipped=True)


@dataclasses.dataclass(frozen=True)
class CredentialStatus:
    """What the credential file says about its own remaining life — and nothing else.

    Exactly two values are lifted out of it (``expiresAt``, ``refreshTokenExpiresAt``,
    both epoch **milliseconds**).  No token, no scope list, no subscription field, and
    nothing from the ``mcpOAuth`` block ever enters this object, so nothing a smoke
    run prints or logs can carry one (ADR-0004).
    """

    found: bool
    readable: bool
    expires_at_ms: int | None = None
    refresh_expires_at_ms: int | None = None
    detail: str = ""


def read_credential_status(path: str | Path | None = None) -> CredentialStatus:
    """Read the two expiry timestamps from *path* (default ``~/.claude/.credentials.json``).

    Zero cost and no spawn.  Every failure to read is reported as a failure to read —
    a missing, locked or shapeless file gives ``found``/``readable``/values that say so,
    never a silent default that would let the gate pass by absence.
    """
    p = Path(path) if path is not None else Path.home() / ".claude" / ".credentials.json"
    if not p.is_file():
        return CredentialStatus(
            found=False, readable=False, detail=f"no credential file at {p.name}"
        )
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return CredentialStatus(found=True, readable=False, detail=f"{type(exc).__name__}")
    block = data.get(_CRED_BLOCK) if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return CredentialStatus(
            found=True, readable=True, detail=f"no {_CRED_BLOCK} block in the credential file"
        )

    def _ms(key: str) -> int | None:
        value = block.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    return CredentialStatus(
        found=True,
        readable=True,
        expires_at_ms=_ms(_CRED_EXPIRES_AT),
        refresh_expires_at_ms=_ms(_CRED_REFRESH_EXPIRES_AT),
    )


# ---------------------------------------------------------------------------
# Pure assertions — observation -> SmokeResult (unit-tested directly)
# ---------------------------------------------------------------------------


def _hms(seconds: float) -> str:
    """A duration as ``1d 2h`` / ``3h 4m`` / ``5m`` — coarse on purpose."""
    seconds = int(seconds)
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{sign}{days}d {hours}h"
    if hours:
        return f"{sign}{hours}h {minutes}m"
    return f"{sign}{minutes}m"


def assert_credential_live(
    status: CredentialStatus,
    *,
    now_s: float | None = None,
    min_ttl_s: float = CREDENTIAL_MIN_TTL_S,
) -> SmokeResult:
    """The seat has enough credential life left to be worth spending against.

    FATH-B04(a), open since the first triage pass and recurring since: nothing checked
    remaining credential life before a matrix started, so a run began, spawned, and
    died on auth — repeatedly, and once "for the third and fourth time in one day".

    What decides it is the **refresh** window, not the access token: the CLI refreshes
    an expired access token on demand, so a short-lived one is normal.  A refresh token
    that has expired is a dead seat, and the only cure is re-authentication.
    """
    name = "credential has life left (free, no spawn)"
    now = time.time() if now_s is None else now_s
    reauth = "re-authenticate (`claude` once, interactively), then re-run"

    if not status.found:
        return SmokeResult(name, False, f"{status.detail}; {reauth}")
    if not status.readable:
        return SmokeResult(name, False, f"credential file unreadable ({status.detail}); {reauth}")
    if status.expires_at_ms is None and status.refresh_expires_at_ms is None:
        return SmokeResult(
            name,
            False,
            f"credential carries neither {_CRED_EXPIRES_AT} nor {_CRED_REFRESH_EXPIRES_AT} "
            f"({status.detail or 'unexpected shape'}), so its life cannot be checked; {reauth}",
        )

    access_left = None if status.expires_at_ms is None else status.expires_at_ms / 1000.0 - now
    refresh_left = (
        None
        if status.refresh_expires_at_ms is None
        else status.refresh_expires_at_ms / 1000.0 - now
    )
    shape = (
        f"access {'n/a' if access_left is None else _hms(access_left)}, "
        f"refresh {'n/a' if refresh_left is None else _hms(refresh_left)}"
    )

    if refresh_left is None:
        # No refresh window to fall back on: the access token is the whole life.
        if access_left is None or access_left < min_ttl_s:
            return SmokeResult(name, False, f"{shape}; under {_hms(min_ttl_s)}; {reauth}")
        return SmokeResult(name, True, shape)
    if refresh_left <= 0:
        return SmokeResult(name, False, f"{shape}; the refresh token has expired; {reauth}")
    if refresh_left < min_ttl_s:
        return SmokeResult(
            name,
            False,
            f"{shape}; less than the {_hms(min_ttl_s)} this gate requires before spend; {reauth}",
        )
    return SmokeResult(name, True, shape)


def assert_isolated_config_is_credential_only(contents: list[str]) -> SmokeResult:
    """The temp ``CLAUDE_CONFIG_DIR`` holds exactly the credential and nothing else.

    Anything beyond ``.credentials.json`` at the top level (CLAUDE.md,
    settings.json, history) would leak user context into the supposedly clean
    arms — the "clean config" claim asserted instead of assumed (ADR-0004).
    """
    ok = contents == [".credentials.json"]
    return SmokeResult("isolated config is credential-only", ok, f"copied={contents}")


def assert_authed_completes(record: RunRecord) -> SmokeResult:
    """A spawn under the credential-only config is authenticated and completed.

    ``OK`` means the credential carried over and the agent finished; an
    ``INFRASTRUCTURE`` status here is an auth/usage-limit failure (a dead config),
    not a task outcome.
    """
    ok = record.status is ExitStatus.OK
    return SmokeResult(
        "credential-only spawn authenticates & completes",
        ok,
        f"status={record.status.value} turns={record.num_turns} result={record.result_text[:80]!r}",
    )


def assert_activity_detected(record: RunRecord) -> SmokeResult:
    """The stream-json parser recovered activity from a spawn that actually ran.

    Two changes from the version that passed hollow.  **Liveness first**: a spawn with
    an ``INFRASTRUCTURE`` status never authenticated, so its stream proves nothing about
    the parser and the check is SKIPPED rather than concluded either way.  **Tokens, not
    turns**: a turn count comes from the harness's own accounting and was ``1`` on a spawn
    that reached no model, while tokens are emitted only by a spawn the model answered.
    The recorded hollow pass was exactly ``turns=1 tokens_in=0 tokens_out=0``.
    """
    name = "stream parsing detects activity"
    shape = f"turns={record.num_turns} tokens_in={record.tokens_in} tokens_out={record.tokens_out}"
    if record.status is not ExitStatus.OK:
        return _skipped(name, f"status={record.status.value} {shape}")
    ok = record.tokens_out > 0 or record.tokens_in > 0
    return SmokeResult(name, ok, shape)


def assert_tool_denied(leaked_files: list[str], record: RunRecord) -> SmokeResult:
    """Default-deny + explicit disallow refused the write: no file was created.

    Gated on liveness for the same reason: "no file was created" is what a spawn that
    never ran produces, so on a dead spawn the empty leak list is the absence of a tool
    call, not the refusal of one.  SKIPPED, not PASS.
    """
    name = "disallowed tool refused under default-deny"
    shape = f"files_created={leaked_files} status={record.status.value}"
    if record.status is not ExitStatus.OK:
        return _skipped(name, shape)
    return SmokeResult(name, not leaked_files, shape)


def assert_concurrency_exclusion() -> SmokeResult:
    """One holder at a time, and a dead holder's claim is released, not waited on.

    Exercised against a scratch lock directory, so it costs nothing and needs no seat —
    which is exactly why it can ship now.  The three deadlocks this mechanism answers
    were all decidable from the lock's own timestamps and were not decided, because
    nothing recorded whether a holder was alive.
    """
    from fathom import runlock

    name = "concurrency exclusion: one run per bank, dead holders released"
    scratch = Path(tempfile.mkdtemp(prefix="fathom-smoke-lock-"))
    try:
        first = runlock.RunLock("smoke", lock_root=scratch, label="smoke holder")
        first.acquire(timeout_s=5.0, poll_s=0.02)
        try:
            second = runlock.RunLock("smoke", lock_root=scratch, label="smoke waiter")
            try:
                second.acquire(timeout_s=0.3, poll_s=0.02)
            except runlock.LockTimeout:
                excluded = True
            else:
                second.release()
                excluded = False
        finally:
            first.release()

        # A ticket whose holder stopped beating must expire from its own timestamp.
        stale_dir = runlock.lock_dir_for("stale", scratch)
        stale_dir.mkdir(parents=True, exist_ok=True)
        dead = stale_dir / "00000000000000000001-0000001-deadbeef.ticket.json"
        dead.write_text(
            json.dumps(
                {
                    "pid": 1,
                    "created_ns": 1,
                    "heartbeat_s": time.time() - runlock.STALE_AFTER_S - 10,
                    "host": "",
                    "label": "a holder that died without releasing",
                }
            ),
            encoding="utf-8",
        )
        third = runlock.RunLock("stale", lock_root=scratch)
        try:
            third.acquire(timeout_s=5.0, poll_s=0.02)
            released = not dead.exists()
        except runlock.LockTimeout:
            released = False
        finally:
            third.release()
    finally:
        cleanup_dir(str(scratch))

    ok = excluded and released
    return SmokeResult(
        name,
        ok,
        f"second acquirer excluded={excluded} dead holder released={released} "
        f"(horizon {runlock.STALE_AFTER_S:.0f}s, beat every "
        f"{runlock.HEARTBEAT_INTERVAL_S:.0f}s)",
    )


def permission_mode_of(argv: list[str]) -> str | None:
    """The value following ``--permission-mode`` in *argv*, or None if absent."""
    for i, tok in enumerate(argv):
        if tok == "--permission-mode" and i + 1 < len(argv):
            return argv[i + 1]
    return None


def injection_file_of(argv: list[str]) -> str | None:
    """The --append-system-prompt-file value in *argv*, or None (K7 guard helper)."""
    if "--append-system-prompt-file" in argv:
        i = argv.index("--append-system-prompt-file")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def assert_injection_armed(argv: list[str], record: RunRecord) -> SmokeResult:
    """A treatment spawn is genuinely armed (K7).

    Requires both halves: ``--append-system-prompt-file`` reached the real CLI argv
    AND the injected directive influenced generation (the canary token appears in the
    reply, on an ``OK`` spawn). Argv presence alone only proves command assembly
    (already unit-tested); the canary proves the live CLI accepted the flag and the
    body reached the model. An arm that spawned un-injected would score as the control
    and silently invalidate the comparison (the matrix-run-1 unarmed-arms defect, D1).
    """
    flag = injection_file_of(argv)
    canary = INJECTION_CANARY in (record.result_text or "")
    ok = flag is not None and record.status is ExitStatus.OK and canary
    return SmokeResult(
        "system-prompt injection reaches the model (treatment armed)",
        ok,
        f"flag_in_argv={flag is not None} status={record.status.value} "
        f"canary_present={canary} result={record.result_text[:80]!r}",
    )


def parse_init_skills(lines: Iterable[str]) -> list[str]:
    """Extract the ``skills`` list from the init event in a stream-json output.

    Returns skill names the spawn reports as available.  Returns an empty list
    if no init event is found or if its ``skills`` field is absent or not a list.
    The init event is emitted before any model turn, so this is model-agnostic
    (spec §5 — "the assertion reads the init event (model-agnostic)").
    """
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("type") == "system" and obj.get("subtype") == "init":
            skills = obj.get("skills")
            if isinstance(skills, list):
                return [str(s) for s in skills if s]
            return []
    return []


def assert_canary_skill_mounted(skills: list[str]) -> SmokeResult:
    """The canary plugin's skill appears in the init-event skills list (treatment).

    A missing canary means ``--plugin-dir`` did not register the plugin at the
    CLI init layer — the treatment arm would be silently unarmed (no discipline
    skills available to trigger), invalidating the arm's contribution to the
    contrast (ADR-0006, spec §5).
    """
    ok = CANARY_SKILL in skills
    return SmokeResult(
        "mount/available: canary skill listed in init event (treatment)",
        ok,
        f"canary={CANARY_SKILL!r} found={ok} skills_count={len(skills)}",
    )


def assert_canary_skill_absent(skills: list[str]) -> SmokeResult:
    """The canary plugin's skill is absent from the control spawn's init event.

    If the canary appears without a mount it means the plugin leaked from the
    user config or was already installed globally — the control is contaminated.
    """
    ok = CANARY_SKILL not in skills
    return SmokeResult(
        "mount/available: canary skill absent without mount (control)",
        ok,
        f"canary={CANARY_SKILL!r} found={CANARY_SKILL in skills} skills_count={len(skills)}",
    )


def assert_no_bypass_in_engine_spawn(
    recorded_argvs: list[list[str]], *, non_bypass_mode: str = NON_BYPASS_PERMISSION_MODE
) -> SmokeResult:
    """Every engine-spawned ``claude`` argv carries the pinned non-bypass mode.

    A pass requires: at least one recorded spawn (the boundary was exercised),
    every spawn carrying ``--permission-mode <non_bypass_mode>``, and none
    carrying ``--dangerously-skip-permissions`` or a ``bypassPermissions`` mode
    (the engine's own default, which the §6 executor must override).
    """
    name = "engine-boundary: non-bypass permission mode reaches the spawned CLI"
    if not recorded_argvs:
        return SmokeResult(
            name, False, "engine spawned no claude invocation (boundary not exercised)"
        )

    problems: list[str] = []
    modes: list[str | None] = []
    for argv in recorded_argvs:
        mode = permission_mode_of(argv)
        modes.append(mode)
        if _BYPASS_FLAG in argv:
            problems.append(_BYPASS_FLAG)
        if mode is None:
            problems.append("missing --permission-mode")
        elif mode != non_bypass_mode:
            # Covers bypassPermissions and any other unexpected (non-pinned) mode.
            problems.append(f"--permission-mode {mode!r}")

    ok = not problems
    detail = f"{len(recorded_argvs)} engine claude spawn(s); permission-mode(s)={modes}"
    if problems:
        detail += "; VIOLATIONS=" + ", ".join(sorted(set(problems)))
    return SmokeResult(name, ok, detail)


# ---------------------------------------------------------------------------
# Probe seam — the real I/O, injected so run_smoke is unit-testable with stubs
# ---------------------------------------------------------------------------


class SmokeProbes(Protocol):
    """The real-spawn surface, injectable so :func:`run_smoke` runs with stubs.

    Each method performs one real observation; :func:`run_smoke` feeds the
    observations to the pure assertions above.  ``RealProbes`` wires the
    credential-only spawns and the engine-boundary shim; tests pass a stub.
    """

    def credential_status(self) -> CredentialStatus:
        """The two expiry timestamps of the real credential (free; no spawn)."""
        ...

    def isolated_config_contents(self) -> list[str]:
        """Sorted top-level names in a freshly made isolated config dir."""
        ...

    def authed_spawn(self) -> RunRecord:
        """A tiny real spawn under the credential-only config."""
        ...

    def deny_spawn(self) -> tuple[list[str], RunRecord]:
        """A real spawn told to write a file under default-deny; (leaked, record)."""
        ...

    def injection_spawn(self) -> tuple[list[str], RunRecord]:
        """A real spawn whose --append-system-prompt-file injects a canary directive;
        returns (recorded argv, record) so the K7 assertion checks wiring and effect."""
        ...

    def mount_treatment_skills(self) -> list[str]:
        """Skills from a real spawn with the canary plugin mounted via --plugin-dir."""
        ...

    def mount_control_skills(self) -> list[str]:
        """Skills from a real spawn without --plugin-dir (canary must be absent)."""
        ...

    def engine_spawn_argvs(self) -> list[list[str]]:
        """Every ``claude`` argv a minimal one-PR engine run spawned (via the shim)."""
        ...


# ---------------------------------------------------------------------------
# Orchestration — run the probes, apply the assertions, report, exit code
# ---------------------------------------------------------------------------


def _guard(label: str, fn: object) -> list[SmokeResult]:
    """Run a probe+assert step; a raised probe becomes a failing result, not a crash."""
    try:
        return fn()  # type: ignore[operator]
    except Exception as exc:
        return [SmokeResult(f"{label} (probe error)", False, f"{type(exc).__name__}: {exc}")]


def run_smoke(
    probes: SmokeProbes,
    *,
    force_fail: bool = False,
    include_engine: bool = True,
    out: TextIO | None = None,
    now_s: float | None = None,
) -> int:
    """Run the smoke assertions against *probes*; print each; return 0/1.

    Returns 0 only when every check was **proven**: a failed check and a skipped
    one both keep it nonzero.  ``force_fail`` appends a failing check (the
    nonzero-path demonstration); ``include_engine`` toggles the engine-boundary
    group (group 5) for environments without the series engine; ``now_s`` pins the
    clock the credential pre-flight compares against (tests).
    """
    _out = out if out is not None else sys.stdout
    results: list[SmokeResult] = []

    # Check 0, first and free: every group below it reads a spawn, and a spawn under
    # a dead credential cannot prove anything the groups below claim to prove.
    results += _guard(
        "credential pre-flight",
        lambda: [assert_credential_live(probes.credential_status(), now_s=now_s)],
    )

    # Operational, free, spawn-free — and it ships in the same release as the lock it
    # checks, which is FATH-B64's own corrected sequencing rule.
    results += _guard("concurrency exclusion", lambda: [assert_concurrency_exclusion()])

    results += _guard(
        "isolated config",
        lambda: [assert_isolated_config_is_credential_only(probes.isolated_config_contents())],
    )

    def _authed() -> list[SmokeResult]:
        # One spawn drives two assertions: authenticated completion + activity.
        record = probes.authed_spawn()
        return [assert_authed_completes(record), assert_activity_detected(record)]

    results += _guard("authed spawn", _authed)

    def _deny() -> list[SmokeResult]:
        leaked, record = probes.deny_spawn()
        return [assert_tool_denied(leaked, record)]

    results += _guard("default-deny spawn", _deny)

    def _injection() -> list[SmokeResult]:
        argv, record = probes.injection_spawn()
        return [assert_injection_armed(argv, record)]

    results += _guard("injection spawn", _injection)

    def _mount() -> list[SmokeResult]:
        treatment_skills = probes.mount_treatment_skills()
        control_skills = probes.mount_control_skills()
        return [
            assert_canary_skill_mounted(treatment_skills),
            assert_canary_skill_absent(control_skills),
        ]

    results += _guard("mount/available", _mount)

    if include_engine:

        def _engine() -> list[SmokeResult]:
            return [assert_no_bypass_in_engine_spawn(probes.engine_spawn_argvs())]

        results += _guard("engine boundary", _engine)

    if force_fail:
        results.append(
            SmokeResult(
                "forced failure (--force-fail)", False, "demonstrates the nonzero-exit path"
            )
        )

    for r in results:
        print(f"[{_label(r)}] {r.name}\n        {r.detail}", file=_out)

    passed = sum(1 for r in results if r.ok)
    failed = [r.name for r in results if not r.ok and not r.skipped]
    skipped = [r.name for r in results if r.skipped]
    all_ok = passed == len(results)
    print("", file=_out)
    # T25c: name them here too. The `7/8` headline read as "mostly fine" precisely
    # because the count travelled without the names, and the count is the line an
    # operator quotes. A verdict a reader has to scroll up to interpret is half a verdict.
    verdict = "ALL PASS" if all_ok else _verdict(failed, skipped)
    print(f"SMOKE RESULT: {verdict} ({passed}/{len(results)} checks)", file=_out)
    return 0 if all_ok else 1


def _label(result: SmokeResult) -> str:
    if result.skipped:
        return "SKIP"
    return "PASS" if result.ok else "FAIL"


def _verdict(failed: list[str], skipped: list[str]) -> str:
    parts = []
    if failed:
        parts.append("FAILED: " + ", ".join(failed))
    if skipped:
        parts.append("SKIPPED (proved nothing): " + ", ".join(skipped))
    return "; ".join(parts) if parts else "SOME FAILED"


# ---------------------------------------------------------------------------
# claude PATH shim — records argv, spends no tokens (engine-boundary mechanism)
# ---------------------------------------------------------------------------


def _recorder_body(record_file: Path) -> str:
    """Python source for the shim: append argv to *record_file*, emit a stub JSON result.

    The recorded argv is what the engine passed to ``claude``; the printed JSON is
    a minimal ``--output-format json`` success so the engine treats the subagent
    as a clean no-op (zero file changes → NOOP) without ever reaching the model.
    """
    rec_literal = repr(str(record_file))
    return (
        "import sys, json\n"
        f"_REC = {rec_literal}\n"
        "try:\n"
        "    with open(_REC, 'a', encoding='utf-8') as _f:\n"
        "        _f.write(json.dumps(sys.argv) + '\\n')\n"
        "except Exception:\n"
        "    pass\n"
        "sys.stdout.write(json.dumps({'result': 'ok', 'total_cost_usd': 0.0, "
        "'usage': {'input_tokens': 1, 'output_tokens': 1}, 'num_turns': 1, "
        "'is_error': False}))\n"
        "sys.stdout.write('\\n')\n"
    )


def _locate_windows_launcher() -> Path | None:
    """Find a distlib console-script launcher (``t*.exe``) to forge ``claude.exe``.

    A bare ``claude`` resolves via CreateProcess, which appends only ``.exe`` (a
    ``.bat``/``.cmd`` shim in PATH is ignored), so the Windows shim must be a real
    ``.exe``.  distlib's launcher stub + an appended ``__main__.py`` zip is the
    standard no-compile way to make one; pip vendors the stubs.
    """
    import sysconfig

    bits = "64" if sys.maxsize > 2**32 else "32"
    arm = "-arm" if platform.machine().lower() in ("arm64", "aarch64") else ""
    names = [f"t{bits}{arm}.exe", f"t{bits}.exe", "t64.exe", "t32.exe"]

    roots: list[Path] = []
    paths = sysconfig.get_paths()
    for key in ("purelib", "platlib"):
        p = paths.get(key)
        if p:
            roots.append(Path(p))
    # A uv-managed venv has no pip of its own, but its *base* interpreter
    # (sys.base_prefix) does — search both prefixes' site-packages so the forge
    # works whether `fathom smoke` runs under the venv or the system Python.
    for prefix in (sys.prefix, sys.base_prefix):
        roots.append(Path(prefix) / "Lib" / "site-packages")
    try:
        import site

        roots += [Path(p) for p in site.getsitepackages()]
        user = site.getusersitepackages()
        if user:
            roots.append(Path(user))
    except Exception:  # noqa: S110 - site dirs are best-effort; purelib usually suffices
        pass

    for root in roots:
        distlib = root / "pip" / "_vendor" / "distlib"
        for name in names:
            cand = distlib / name
            if cand.is_file():
                return cand
    return None


def forge_claude_shim(shim_dir: Path, record_file: Path) -> Path:
    """Write an executable ``claude`` shim into *shim_dir* that records argv.

    POSIX: a ``#!``-headed script.  Windows: a forged ``claude.exe`` (distlib
    launcher stub + shebang + an appended zip whose ``__main__.py`` is the
    recorder).  Returns the shim path.  Raises if a Windows launcher stub cannot
    be located.
    """
    body = _recorder_body(record_file)
    if os.name == "nt":
        launcher = _locate_windows_launcher()
        if launcher is None:
            raise RuntimeError(
                "cannot forge a claude.exe shim: no distlib launcher (t*.exe) found "
                "under any site-packages/pip/_vendor/distlib"
            )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            z.writestr("__main__.py", body)
        shebang = b"#!" + sys.executable.encode("utf-8") + b"\r\n"
        shim = shim_dir / "claude.exe"
        shim.write_bytes(launcher.read_bytes() + shebang + buf.getvalue())
        return shim
    shim = shim_dir / "claude"
    shim.write_text("#!" + sys.executable + "\n" + body, encoding="utf-8")
    shim.chmod(0o755)
    return shim


def read_argv_log(record_file: Path) -> list[list[str]]:
    """Parse the shim's argv log (one JSON array per spawn) into a list of argvs."""
    path = Path(record_file)
    if not path.exists():
        return []
    out: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            argv = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(argv, list):
            out.append([str(x) for x in argv])
    return out


def _write_smoke_task_assets(task_dir: Path) -> None:
    """Write the minimal one-PR series assets the engine-boundary run instantiates."""
    (task_dir / "series.toml").write_text(_SMOKE_SERIES_TEMPLATE, encoding="utf-8")
    prompts = task_dir / "prompts"
    prompts.mkdir()
    (prompts / "PR01.md").write_text(
        "# Smoke probe PR\n\nThis is a no-op smoke probe. Make no changes.\n", encoding="utf-8"
    )
    fixtures = task_dir / "fixtures"
    fixtures.mkdir()
    (fixtures / "README.md").write_text("# fathom smoke fixture\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# RealProbes — the live spawns (exercised by `fathom smoke`, stubbed in tests)
# ---------------------------------------------------------------------------


def _smoke_scenario(model: str, effort: str, timeout_s: float) -> ResolvedScenario:
    """A minimal resolved scenario; only model/effort/timeout are read by the adapter."""
    return ResolvedScenario(
        name="smoke",
        adapter="claude-cli",
        model=model,
        strategy="single-session",
        effort=effort,
        tools=ToolsConfig(source="none"),
        limits=LimitsOverride(trial_timeout_s=int(timeout_s)),
        model_id=None,
        tool_repo_sha=None,
        tool_invocation_cmd=None,
        config_hash="0" * 64,
    )


class RealProbes:
    """Live smoke probes: real credential-only spawns + the engine-boundary shim run.

    Not unit-tested (that is what ``fathom smoke`` is for); the assertions and
    :func:`run_smoke` plumbing it feeds are tested with a stub implementing
    :class:`SmokeProbes`.
    """

    def __init__(
        self,
        *,
        model: str = DEFAULT_SMOKE_MODEL,
        effort: str = DEFAULT_SMOKE_EFFORT,
        scenarios_dir: Path = Path("scenarios"),
        real_config_dir: str | None = None,
        spawn_timeout_s: float = DEFAULT_SPAWN_TIMEOUT_S,
        engine_timeout_s: float = DEFAULT_ENGINE_TIMEOUT_S,
    ) -> None:
        self.model = model
        self.effort = effort
        self.scenarios_dir = Path(scenarios_dir)
        self.real_config_dir = real_config_dir
        self.spawn_timeout_s = spawn_timeout_s
        self.engine_timeout_s = engine_timeout_s

    def _scenario(self) -> ResolvedScenario:
        return _smoke_scenario(self.model, self.effort, self.spawn_timeout_s)

    # -- group 0 (credential life; free, no spawn) --------------------------

    def credential_status(self) -> CredentialStatus:
        # Reads the SAME file `make_isolated_config` copies, so the pre-flight and
        # the spawns below it cannot disagree about which credential is in play.
        real = Path(self.real_config_dir) if self.real_config_dir else Path.home() / ".claude"
        return read_credential_status(real / ".credentials.json")

    # -- group 1 (config) ---------------------------------------------------

    def isolated_config_contents(self) -> list[str]:
        cfg = make_isolated_config(self.real_config_dir)
        try:
            return sorted(p.name for p in Path(cfg).iterdir())
        finally:
            cleanup_dir(cfg)

    # -- group 1/3 (authed spawn) -------------------------------------------

    def authed_spawn(self) -> RunRecord:
        runner = ClaudeCliRunner(
            allowed_tools=(),
            disallowed_tools=(),
            real_config_dir=self.real_config_dir,
            max_attempts=2,
            default_max_turns=2,
            default_max_budget_usd=0.5,
            default_timeout_s=self.spawn_timeout_s,
            stream=True,
        )
        ws = Path(tempfile.mkdtemp(prefix="fathom-smoke-authed-"))
        try:
            return runner.execute("Reply with the single word: hi.", ws, self._scenario())
        finally:
            cleanup_dir(str(ws))

    # -- group 2 (default-deny) ---------------------------------------------

    def deny_spawn(self) -> tuple[list[str], RunRecord]:
        runner = ClaudeCliRunner(
            allowed_tools=("Read",),
            disallowed_tools=("Write", "Edit", "Bash", "NotebookEdit"),
            real_config_dir=self.real_config_dir,
            max_attempts=1,
            default_max_turns=3,
            default_max_budget_usd=0.5,
            default_timeout_s=self.spawn_timeout_s,
            stream=True,
        )
        ws = Path(tempfile.mkdtemp(prefix="fathom-smoke-deny-"))
        try:
            record = runner.execute(
                "Create a file named probe.txt in the current directory containing the word "
                '"leak". Use the Write tool. Do not ask for confirmation.',
                ws,
                self._scenario(),
            )
            leaked = sorted(p.name for p in ws.rglob("*") if p.is_file())
            return leaked, record
        finally:
            cleanup_dir(str(ws))

    # -- group: treatment arm is armed (injection reaches the model) --------

    def injection_spawn(self) -> tuple[list[str], RunRecord]:
        """Real spawn whose --append-system-prompt-file carries a canary directive.

        A recording wrapper around the real subprocess boundary captures the argv
        (proving the flag is assembled and passed through) while the spawn actually
        runs (proving the live CLI accepts the flag and the model obeys the injected
        system prompt). Spends a tiny amount of tokens, like the other adapter spawns.
        """
        from fathom.adapters.claude_cli import _subprocess_spawn

        captured: list[list[str]] = []

        def _recording_spawn(argv, *, input, timeout, env, cwd):  # type: ignore[no-untyped-def]
            captured.append([str(a) for a in argv])
            return _subprocess_spawn(argv, input=input, timeout=timeout, env=env, cwd=cwd)

        inject_dir = Path(tempfile.mkdtemp(prefix="fathom-smoke-inject-"))
        inject_file = inject_dir / "canary.md"
        inject_file.write_text(
            "IMPORTANT INSTRUCTION: end every reply with the exact token "
            f"{INJECTION_CANARY} on its own final line, regardless of anything else.",
            encoding="utf-8",
        )
        runner = ClaudeCliRunner(
            allowed_tools=(),
            disallowed_tools=(),
            real_config_dir=self.real_config_dir,
            append_system_prompt_file=str(inject_file),
            max_attempts=2,
            default_max_turns=2,
            default_max_budget_usd=0.5,
            default_timeout_s=self.spawn_timeout_s,
            stream=True,
            spawn=_recording_spawn,
        )
        ws = Path(tempfile.mkdtemp(prefix="fathom-smoke-inject-ws-"))
        try:
            record = runner.execute("Reply with a brief greeting.", ws, self._scenario())
            return (captured[0] if captured else []), record
        finally:
            cleanup_dir(str(ws))
            cleanup_dir(str(inject_dir))

    # -- group: mount/available (spec §5) -----------------------------------

    def _init_skills_from_spawn(self, plugin_dirs: Sequence[str] = ()) -> list[str]:
        """Run a minimal spawn and return its init-event skill list.

        Captures raw stdout via a recording wrapper (the same pattern as
        :meth:`injection_spawn`) so :func:`parse_init_skills` can read the init
        event before any model output.  The spawn itself completes normally;
        we just need its first stream event, which precedes all model turns.
        """
        from fathom.adapters.claude_cli import _subprocess_spawn

        captured_stdout: list[str] = []

        def _capturing_spawn(argv, *, input, timeout, env, cwd):  # type: ignore[no-untyped-def]
            result = _subprocess_spawn(argv, input=input, timeout=timeout, env=env, cwd=cwd)
            captured_stdout.append(result.stdout or "")
            return result

        runner = ClaudeCliRunner(
            allowed_tools=(),
            disallowed_tools=(),
            real_config_dir=self.real_config_dir,
            plugin_dirs=list(plugin_dirs),
            max_attempts=1,
            default_max_turns=1,
            default_max_budget_usd=0.2,
            default_timeout_s=self.spawn_timeout_s,
            stream=True,
            spawn=_capturing_spawn,
        )
        ws = Path(tempfile.mkdtemp(prefix="fathom-smoke-mount-"))
        try:
            runner.execute("Reply with the single word: ok.", ws, self._scenario())
            stdout = captured_stdout[0] if captured_stdout else ""
            return parse_init_skills(stdout.splitlines())
        finally:
            cleanup_dir(str(ws))

    def mount_treatment_skills(self) -> list[str]:
        return self._init_skills_from_spawn(plugin_dirs=[str(CANARY_PLUGIN_DIR)])

    def mount_control_skills(self) -> list[str]:
        return self._init_skills_from_spawn(plugin_dirs=[])

    # -- group 4/5 (engine boundary) ----------------------------------------

    def engine_spawn_argvs(self) -> list[list[str]]:
        """Drive a minimal one-PR series run with ``claude`` shadowed by the shim.

        Reuses the §6 :class:`SeriesExecutor` so the *real* pinning path is
        exercised: the executor instantiates the series with
        ``permission_mode = "default"``, then the engine subprocess (with the shim
        dir on PATH) resolves ``claude`` to the recorder and we read back its argv.
        """
        from fathom.scenario import load_scenario, resolve_scenario
        from fathom.strategies.series import (
            SeriesExecutor,
            _default_run_engine,
        )
        from fathom.taskbank import Task, stage_task

        shim_dir = Path(tempfile.mkdtemp(prefix="fathom-smoke-shim-"))
        task_dir = Path(tempfile.mkdtemp(prefix="fathom-smoke-task-"))
        record_file = shim_dir / "claude_argv.jsonl"
        try:
            forge_claude_shim(shim_dir, record_file)
            _write_smoke_task_assets(task_dir)
            task = Task(
                id="fathom-smoke",
                instruction="engine-boundary smoke probe",
                limits={},
                verify={"entry": "verify.py"},
                task_dir=task_dir,
            )

            config = load_scenario(self.scenarios_dir / "series.toml")
            scenario = resolve_scenario(config, _DefaultSmokeResolver())
            scenario = dataclasses.replace(
                scenario, limits=LimitsOverride(trial_timeout_s=int(self.engine_timeout_s))
            )

            def shim_engine(argv, *, cwd, env, timeout):  # type: ignore[no-untyped-def]
                # The engine resolves `claude` against ITS OWN process PATH, so the
                # shim dir must lead the PATH the engine child is launched with.
                patched = {**env, "PATH": str(shim_dir) + os.pathsep + env.get("PATH", "")}
                return _default_run_engine(argv, cwd=cwd, env=patched, timeout=timeout)

            executor = SeriesExecutor(run_engine=shim_engine, real_config_dir=self.real_config_dir)
            with stage_task(task, "main") as workspace:
                # The series executor ignores the Runner (the engine spawns claude
                # itself — ADR-0001); the recorded argv is read regardless of the
                # trial verdict, so a downstream engine failure cannot hide a bypass.
                executor.run_trial(task, workspace, scenario, None)  # type: ignore[arg-type]

            return read_argv_log(record_file)
        finally:
            cleanup_dir(str(shim_dir))
            cleanup_dir(str(task_dir))


class _DefaultSmokeResolver:
    """Scenario resolver for the engine-boundary run (real git SHA + uv invocation)."""

    def resolve_model_id(self, model: str) -> str | None:
        return None

    def resolve_tool_repo_sha(self, repo: str) -> str:
        import subprocess

        result = subprocess.run(
            ["git", "-C", repo, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"

    def build_tool_invocation_cmd(self, repo: str) -> str:
        from fathom.scenario import resolve_repo_invocation_cmd

        return resolve_repo_invocation_cmd(repo)


# ---------------------------------------------------------------------------
# CLI entry (also reachable as `fathom smoke`)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Standalone entry: parse smoke flags, run the gate. Returns the exit code."""
    import argparse

    p = argparse.ArgumentParser(
        prog="fathom smoke", description="Real-spawn isolation smoke gate (spec §11)"
    )
    p.add_argument(
        "--force-fail",
        action="store_true",
        help="Append a forced failing check to demonstrate the nonzero exit path",
    )
    p.add_argument(
        "--no-engine-boundary",
        action="store_true",
        help="Skip the engine-boundary assertion (group 4)",
    )
    p.add_argument("--model", default=DEFAULT_SMOKE_MODEL, help="Model for the real spawns")
    p.add_argument("--effort", default=DEFAULT_SMOKE_EFFORT, help="Effort for the real spawns")
    args = p.parse_args(argv)

    probes = RealProbes(model=args.model, effort=args.effort)
    return run_smoke(probes, force_fail=args.force_fail, include_engine=not args.no_engine_boundary)


if __name__ == "__main__":
    sys.exit(main())
