"""Series-engine strategy executor (spec §6).

This is the ONE sanctioned non-adapter model-call path in fathom (Invariants /
ADR-0001): the series engine spawns the ``claude`` CLI itself, so the run does
not go through a Runner.  The review grep treats this module as the named waiver;
no other module may spawn a model.  The engine is a black-box subprocess — fathom
never imports it; the binary is named entirely in the scenario (``[tools].repo`` +
the resolved invocation command), so no engine name appears in ``src/``.  The two
formats fathom speaks across that boundary — the ``series.toml`` it writes and the
``spawns.jsonl`` telemetry it reads — are the engine-neutral series contract
(``docs/specs/2026-07-03-series-engine-contract.md``).

The executor's whole job is to make the engine's behaviour *measurable and
comparable* rather than accept its operator-friendly defaults:

* **Assets outside the workspace.**  The engine's series.toml, prompt files, and
  outputs directory are instantiated in a sibling temp dir and referenced by
  absolute paths, so no engine input or output asset ever lands in the scored
  workspace (the verifier, §7, would otherwise fingerprint the scenario).
  Absolute ``[paths]`` survive the engine's ``repo_root / path`` join (an absolute
  right operand replaces the root), so outputs land outside the cwd.
* **Every comparison-relevant field pinned.**  The engine may default to a strong
  model, max effort, an auto-approve permission mode, and its own per-spawn
  budgets — accepting any of them would silently diverge the arm.  We pin a
  non-bypass permission mode, the scenario's model/effort, fixed per-spawn budgets,
  and strip any per-PR model/effort/budget override so every subagent runs at the
  pinned settings (cross-arm parity, §4).
* **Run records from matching spawn events only.**  A ``spawns.jsonl`` accumulates
  ``spawn_complete`` events across invocations (each also carries the lifecycle
  ``run_start`` / ``run_complete``).  We materialize one run record per
  ``spawn_complete`` whose run id is this invocation's (the most recent run in the
  file), marked with the weaker series pin (requested model string, no cache-token
  split).
* **Infrastructure failures classified before scoring.**  The engine surfaces an
  auth / subscription usage-limit / retry-exhaustion halt as a distinct exit code
  and a ``run_complete`` ``outcome = "infrastructure"``; we reclassify such a trial
  as a §5-style infrastructure error that stops the matrix cleanly (§10) rather
  than scoring it as a task failure.
* **Whole-tree kill on timeout.**  On trial timeout the engine *and* its spawned
  ``claude`` grandchild are terminated; killing only the direct child would
  orphan the CLI.

Stdlib only.  The engine subprocess is injectable so every test runs with a stub
— no real engine runs here (that is the smoke gate's job, §11).
"""

from __future__ import annotations

import dataclasses
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import time
import tomllib
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.adapters.claude_cli import _classify_infrastructure as _classify_infra
from fathom.adapters.claude_cli import (
    cleanup_dir,
    make_isolated_config,
    make_spawn_env,
    pid_alive,
    terminate_process_tree,
)
from fathom.adapters.claude_cli import terminate_process_tree as _terminate_tree
from fathom.strategies.base import PIN_SERIES, TrialResult, TrialStatus

# Re-exported for callers/tests that import them from this module (historical home).
__all__ = ["pid_alive", "terminate_process_tree"]

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fathom.adapters.base import Runner
    from fathom.scenario import ResolvedScenario
    from fathom.taskbank import Task

# A non-bypass permission mode with the same default-deny philosophy as the other
# arms: tools not on the allow list are refused (an engine that defaults to
# ``bypassPermissions`` auto-approves everything and is never accepted — §6).
NON_BYPASS_PERMISSION_MODE = "default"

# Pinned per-spawn budgets (USD, as TOML numbers — the series spec validates
# ``[governance.budgets]`` as floats and rejects quoted strings).  The resolved
# scenario carries model/effort but no budget field (§4 schema), so these are
# pinned here; constructor-injectable to keep them an explicit, recorded choice
# instead of the engine's silent defaults.
DEFAULT_BUDGET_IMPL = 20.0
DEFAULT_BUDGET_REVIEW = 5.0
DEFAULT_BUDGET_FIX = 3.0

# Per-PR keys stripped from the template so every subagent runs at the
# scenario-pinned model/effort/budget — otherwise the series arm could silently
# use a different (e.g. stronger) model per PR and the comparison would measure
# models, not strategies (§4 parity).  The engine also rejects these at spec-load;
# stripping is belt-and-braces so a stray override fails no trial.
_PER_PR_PINS = ("model", "tier", "effort", "budget", "budgets")

# Default committed-template filename under a task's directory (§12).
DEFAULT_TEMPLATE_NAME = "series.toml"

# The engine's exit-code taxonomy (series contract §7): 0 integrated · 1 blocked
# (a blocking gate stayed red — a scored task failure) · 2 infrastructure
# (auth / usage-limit / retry — halt the matrix cleanly) · 3 usage (a malformed
# series.toml — fathom's own bug, surfaced loudly, never scored as the task) ·
# 4 budget (a spawn hit its per-spawn --max-budget-usd cap; convoy leaves the
# partial work un-integrated). A budget truncation is a governance halt, not a
# task result — classified ERRORED with a clear detail so it is excluded from the
# pass rate (report.py counts only status=="completed") rather than falling
# through to an opaque "engine exit 4" that reads as a task failure; it is
# trial-specific, so unlike infrastructure it does NOT halt the whole matrix.
ENGINE_EXIT_BLOCKED = 1
ENGINE_EXIT_INFRASTRUCTURE = 2
ENGINE_EXIT_USAGE = 3
ENGINE_EXIT_BUDGET = 4


# ---------------------------------------------------------------------------
# Engine subprocess boundary — injectable; whole-process-tree kill on timeout
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class EngineOutcome:
    """Result of one engine invocation (mirrors the slice the executor needs)."""

    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    duration_s: float = 0.0


class EngineRunner(Protocol):
    """The engine subprocess boundary, injectable so tests run with a stub.

    An implementation runs ``argv`` (the pinned ``<engine> run <series.toml>``)
    with ``cwd`` as the trial workspace and ``env`` carrying the isolated
    ``CLAUDE_CONFIG_DIR``, enforcing ``timeout`` by terminating the whole process
    tree, and returns an :class:`EngineOutcome`.
    """

    def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: str,
        env: Mapping[str, str],
        timeout: float | None,
    ) -> EngineOutcome: ...


def _default_run_engine(
    argv: Sequence[str],
    *,
    cwd: str,
    env: Mapping[str, str],
    timeout: float | None,
) -> EngineOutcome:
    """Default engine boundary: run ``argv``, kill the whole tree on timeout."""
    popen_kwargs: dict[str, Any] = {}
    if os.name != "nt":
        # Own session/group so a timeout can killpg the engine + its claude child.
        popen_kwargs["start_new_session"] = True
    start = time.monotonic()
    proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
        list(argv),
        cwd=cwd,
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        **popen_kwargs,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        return EngineOutcome(
            returncode=proc.returncode,
            stdout=out or "",
            stderr=err or "",
            timed_out=False,
            duration_s=time.monotonic() - start,
        )
    except subprocess.TimeoutExpired:
        _terminate_tree(proc.pid)
        try:
            out, err = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
        return EngineOutcome(
            returncode=proc.returncode if proc.returncode is not None else -1,
            stdout=out or "",
            stderr=err or "",
            timed_out=True,
            duration_s=time.monotonic() - start,
        )


# ---------------------------------------------------------------------------
# Minimal TOML writer (stdlib tomllib only reads) — series.toml subset
# ---------------------------------------------------------------------------


def _fmt_str(s: str) -> str:
    """A TOML basic string with the load-bearing escapes (backslash first)."""
    esc = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{esc}"'


def _fmt(value: Any) -> str:
    """Format a scalar (or array of scalars) as TOML.  bool before int."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return _fmt_str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_fmt(x) for x in value) + "]"
    raise TypeError(f"unserializable TOML value: {value!r}")


def _partition(table: dict) -> tuple[list, list, list]:
    """Split a table's items into (scalars, sub-tables, arrays-of-tables)."""
    scalars, subtables, arraytables = [], [], []
    for key, val in table.items():
        if isinstance(val, dict):
            subtables.append((key, val))
        elif isinstance(val, list) and val and all(isinstance(x, dict) for x in val):
            arraytables.append((key, val))
        else:
            scalars.append((key, val))
    return scalars, subtables, arraytables


def _emit_table(table: dict, path: list[str], out: list[str], *, is_array_elem: bool) -> None:
    scalars, subtables, arraytables = _partition(table)
    if is_array_elem:
        out.append(f"[[{'.'.join(path)}]]\n")
    elif path and (scalars or not (subtables or arraytables)):
        out.append(f"[{'.'.join(path)}]\n")
    for key, val in scalars:
        out.append(f"{key} = {_fmt(val)}\n")
    if (path or is_array_elem) and scalars:
        out.append("\n")
    for key, val in subtables:
        _emit_table(val, [*path, key], out, is_array_elem=False)
    for key, val in arraytables:
        for elem in val:
            _emit_table(elem, [*path, key], out, is_array_elem=True)


def dump_toml(data: dict) -> str:
    """Serialize a parsed-series.toml-shaped dict back to TOML text.

    Handles exactly the value types a series.toml carries: scalars, arrays of
    scalars, tables, and arrays of tables.  A table's scalar keys are emitted
    before any nested ``[table]`` / ``[[array]]`` header so they attribute
    correctly (the one real TOML ordering constraint).
    """
    out: list[str] = []
    _emit_table(data, [], out, is_array_elem=False)
    return "".join(out)


# ---------------------------------------------------------------------------
# spawns.jsonl → run records
# ---------------------------------------------------------------------------


def _read_events(telemetry_path: Path) -> list[dict]:
    """Read spawns.jsonl into a list of event dicts, skipping malformed lines."""
    if not telemetry_path.exists():
        return []
    events: list[dict] = []
    with telemetry_path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError) as exc:
                warnings.warn(
                    f"Skipping malformed telemetry line {telemetry_path}:{lineno}: {exc}",
                    stacklevel=2,
                )
                continue
            if isinstance(obj, dict):
                events.append(obj)
    return events


def _run_ids(events: list[dict]) -> set[str]:
    return {str(e["run_id"]) for e in events if e.get("run_id")}


def _select_run_id(events: list[dict], pre_ids: set[str]) -> str | None:
    """Pick this invocation's run id: the most-recent run not present beforehand.

    A fresh per-trial outputs dir holds exactly one run, so this is normally the
    only id; the ``pre_ids`` subtraction and the ``max`` (run ids are
    lexicographically-sortable ``%Y%m%dT%H%M%SZ`` stamps plus a random suffix, so
    ``max`` is the latest) make the choice robust to a telemetry file that
    accumulated a foreign run from an earlier invocation — that older / pre-existing
    id is excluded.
    """
    ids = _run_ids(events)
    candidates = ids - pre_ids
    pool = candidates or ids
    return max(pool) if pool else None


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _event_to_record(event: dict) -> RunRecord:
    """Materialize one ``spawn_complete`` event into a RunRecord (series pin).

    The weaker series pin shows up here: ``model_id`` is the *requested* model
    string (the engine reports no exact CLI id per subagent) and ``tokens_cache``
    is 0 (the telemetry has no read/creation cache split).  The whole event is kept
    in ``usage`` so a downstream consumer can recover any field this does not name
    (e.g. the engine's ``cost_estimated`` flag on a subscription-estimated cost).
    """
    exit_code = _as_int(event.get("exit_code", 0))
    status = ExitStatus.OK if exit_code == 0 else ExitStatus.ERROR
    model = str(event.get("effective_model") or event.get("model") or "")
    return RunRecord(
        status=status,
        tokens_in=_as_int(event.get("input_tokens", 0)),
        tokens_out=_as_int(event.get("output_tokens", 0)),
        tokens_cache=0,
        num_turns=_as_int(event.get("num_turns", 0)),
        duration_s=_as_float(event.get("duration_s", 0.0)),
        cost_usd_est=_as_float(event.get("cost_usd", 0.0)),
        model_id=model,
        cli_version="",
        result_text=f"role={event.get('role', '')} pr={event.get('pr_id', '')}".strip(),
        usage=dict(event),
    )


def _materialize_runs(events: list[dict], run_id: str | None) -> list[RunRecord]:
    """One RunRecord per ``spawn_complete`` event whose run id is ``run_id``.

    Lifecycle events (``run_start`` / ``run_complete``) and foreign-run-id events
    are skipped.
    """
    if run_id is None:
        return []
    return [
        _event_to_record(e)
        for e in events
        if e.get("event") == "spawn_complete" and str(e.get("run_id")) == run_id
    ]


# ---------------------------------------------------------------------------
# Failure classification — infrastructure before scoring (§5/§6/§10)
# ---------------------------------------------------------------------------


def _final_run_outcome(events: list[dict]) -> str | None:
    """The ``outcome`` of the last ``run_complete`` event, or None if absent.

    The engine states its own coarse verdict — ``completed`` / ``blocked`` /
    ``infrastructure`` — on the terminal ``run_complete`` line; the most recent one
    is this invocation's (a fresh per-trial outputs dir holds a single run).
    """
    for event in reversed(events):
        if event.get("event") == "run_complete":
            outcome = event.get("outcome")
            return str(outcome) if outcome is not None else None
    return None


def _classify(outcome: EngineOutcome, events: list[dict]) -> tuple[TrialStatus, str]:
    """Trial verdict from the engine outcome + telemetry events.

    Infrastructure (auth / usage-limit / engine retry-exhaustion) is decided
    *before* a bare nonzero exit is scored: the engine surfaces it explicitly as
    exit code ``2`` and a ``run_complete`` ``outcome = "infrastructure"`` (series
    contract §7), so only a non-infrastructure failure marks the trial errored.
    The engine's own stdout/stderr is scanned for an auth/usage-limit signature as
    a backstop, matching the single-spawn adapter
    (:func:`~fathom.adapters.claude_cli._spawn_is_infrastructure`).
    """
    if outcome.timed_out:
        return TrialStatus.ERRORED, "engine timeout; process tree terminated"

    run_outcome = _final_run_outcome(events)
    own_channel = "\n".join(p for p in (outcome.stdout, outcome.stderr) if p)
    if (
        outcome.returncode == ENGINE_EXIT_INFRASTRUCTURE
        or run_outcome == "infrastructure"
        or _classify_infra(own_channel)
    ):
        return TrialStatus.INFRASTRUCTURE, "engine infrastructure halt (auth/usage-limit/retry)"

    if outcome.returncode == ENGINE_EXIT_USAGE:
        return TrialStatus.ERRORED, "engine usage error (invalid series.toml)"
    if outcome.returncode == ENGINE_EXIT_BUDGET or run_outcome == "budget":
        # A spawn hit its per-spawn budget cap; the engine left the partial work
        # un-integrated (§7). Not a task result — recorded ERRORED (excluded from the
        # pass rate) with a clear detail, and re-runnable after raising --max-budget-usd.
        return TrialStatus.ERRORED, "engine budget cap hit (partial work not integrated)"
    if outcome.returncode != 0:
        # Includes exit 1 (a blocking gate stayed red) — a scored task failure.
        return TrialStatus.ERRORED, f"engine exit {outcome.returncode}"
    return TrialStatus.COMPLETED, ""


# ---------------------------------------------------------------------------
# The executor
# ---------------------------------------------------------------------------


def _abs(path: Path) -> str:
    """Absolute, forward-slash path string (survives the engine's repo_root join)."""
    return str(path.resolve()).replace("\\", "/")


class SeriesExecutor:
    """Drive the series engine over a task's committed series (spec §6).

    Satisfies the :class:`~fathom.strategies.base.StrategyExecutor` protocol.  The
    engine subprocess and the isolated-config helpers are injectable so every
    test runs without a real engine or a real credential.
    """

    def __init__(
        self,
        *,
        run_engine: EngineRunner = _default_run_engine,
        template_name: str = DEFAULT_TEMPLATE_NAME,
        permission_mode: str = NON_BYPASS_PERMISSION_MODE,
        budget_impl: float = DEFAULT_BUDGET_IMPL,
        budget_review: float = DEFAULT_BUDGET_REVIEW,
        budget_fix: float = DEFAULT_BUDGET_FIX,
        assets_root: str | None = None,
        real_config_dir: str | None = None,
        make_config: Any = make_isolated_config,
        cleanup: Any = cleanup_dir,
    ) -> None:
        self.run_engine = run_engine
        self.template_name = template_name
        self.permission_mode = permission_mode
        self.budget_impl = budget_impl
        self.budget_review = budget_review
        self.budget_fix = budget_fix
        self.assets_root = assets_root
        self.real_config_dir = real_config_dir
        self.make_config = make_config
        self.cleanup = cleanup

    # -- StrategyExecutor protocol ------------------------------------------

    def run_trial(
        self,
        task: Task,
        workspace: Path,
        scenario: ResolvedScenario,
        runner: Runner,  # noqa: ARG002 - the engine spawns claude itself (ADR-0001)
    ) -> TrialResult:
        """Instantiate the series outside ``workspace``, run the engine, score it."""
        workspace = Path(workspace)
        template = self._read_template(task)
        assets_dir = Path(
            tempfile.mkdtemp(prefix="fathom-series-", dir=self.assets_root or str(workspace.parent))
        )
        config_dir = self.make_config(self.real_config_dir)
        try:
            series_toml, outputs_dir = self._instantiate(task, template, assets_dir, scenario)
            argv = _build_argv(scenario, series_toml)
            # Same billing/routing-diverter strip as the single-spawn adapter, so the
            # engine's own claude spawns can't be rerouted off the subscription credential.
            env = make_spawn_env(str(config_dir))
            telemetry_path = outputs_dir / "spawns.jsonl"
            pre_ids = _run_ids(_read_events(telemetry_path))

            outcome = self.run_engine(
                argv,
                cwd=str(workspace),
                env=env,
                timeout=scenario.limits.trial_timeout_s,
            )

            events = _read_events(telemetry_path)
            run_id = _select_run_id(events, pre_ids)
            runs = _materialize_runs(events, run_id)
            status, detail = _classify(outcome, events)
            return TrialResult(
                status=status,
                runs=runs,
                pin_level=PIN_SERIES,
                wall_clock_s=outcome.duration_s,
                detail=detail,
            )
        finally:
            self.cleanup(str(config_dir))
            cleanup_dir(str(assets_dir))

    # -- internals ----------------------------------------------------------

    def _read_template(self, task: Task) -> dict:
        with (Path(task.task_dir) / self.template_name).open("rb") as f:
            return tomllib.load(f)

    def _instantiate(
        self,
        task: Task,
        template: dict,
        assets_dir: Path,
        scenario: ResolvedScenario,
    ) -> tuple[Path, Path]:
        """Copy assets into the sibling dir, pin every measured field, write the toml.

        Returns ``(series_toml_path, outputs_dir)``, both absolute and outside the
        trial workspace.
        """
        paths = template.get("paths", {})
        task_dir = Path(task.task_dir)

        # Copy the committed prompts/ out of the task into the sibling assets dir
        # (the workspace must never hold an engine input asset).
        src_prompts = task_dir / paths["prompts"]
        dst_prompts = assets_dir / "prompts"
        shutil.copytree(src_prompts, dst_prompts)

        outputs_dir = assets_dir / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)

        # Absolute paths so the engine's `repo_root / path` join is a no-op and
        # every asset stays outside the cwd (the scored workspace).
        paths["prompts"] = _abs(dst_prompts)
        paths["outputs"] = _abs(outputs_dir)
        template["paths"] = paths

        # Pin the [governance] block — never accept the engine's bypass/strong/max
        # defaults.  Drop `tier` so the explicit model pin is authoritative; budgets
        # are TOML numbers (the spec rejects quoted strings).
        governance = dict(template.get("governance", {}))
        governance.pop("tier", None)
        governance["model"] = scenario.model
        governance["effort"] = scenario.effort
        governance["permission_mode"] = self.permission_mode
        governance["budgets"] = {
            "implementation": self.budget_impl,
            "review": self.budget_review,
            "fix": self.budget_fix,
        }
        template["governance"] = governance

        # Strip per-PR model/effort/budget overrides so every subagent runs at the
        # pinned settings (cross-arm parity, §4).
        for pr in template.get("prs", []):
            for key in _PER_PR_PINS:
                pr.pop(key, None)

        series_toml = assets_dir / "series.toml"
        series_toml.write_text(dump_toml(template), encoding="utf-8")
        # Return the *resolved* outputs path that the toml carries — the engine
        # writes spawns.jsonl to exactly that (`repo_root / abspath` -> abspath),
        # so the executor must read from the same canonicalized location.
        return series_toml, Path(paths["outputs"])


def _build_argv(scenario: ResolvedScenario, series_toml: Path) -> list[str]:
    """``<pinned invocation command> run <series.toml>`` (spec §6).

    Uses the scenario's resolved invocation command (e.g.
    ``uv run --project <repo> convoy``) — never a bare PATH lookup; falls back to
    ``convoy`` only if the scenario left it unset.
    """
    cmd = scenario.tool_invocation_cmd or "convoy"
    return [*shlex.split(cmd), "run", str(series_toml)]
