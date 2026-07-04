"""StrategyExecutor protocol and the trial-level result it returns.

A *strategy* is how a scenario turns one task into one or more model spawns: the
bare/single-long-session arms make a single Runner call, the series arm drives
the engine which spawns the CLI itself.  Each executor implements
``run_trial`` and returns a :class:`TrialResult` carrying the raw per-spawn
:class:`~fathom.adapters.base.RunRecord`\\ s (the economy currency the report
aggregates), the trial-level outcome, and the pin level (``"strong"`` for adapter
runs, ``"series"`` for the weaker-pinned engine runs — spec §6).

The split between :class:`TrialStatus` values mirrors §5/§10: an
``INFRASTRUCTURE`` trial (auth / subscription usage-limit) must never score and
must stop the matrix cleanly, distinct from an ``ERRORED`` trial that is the
run's own fault and is scored.

Stdlib only.
"""

from __future__ import annotations

import dataclasses
import enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from fathom.adapters.base import RunRecord, Runner
    from fathom.scenario import ResolvedScenario
    from fathom.taskbank import Task

# Pin level recorded on every run/trial: adapter spawns carry the strong pin
# (exact CLI-reported model id, cache-token split); engine spawns carry the
# weaker series pin (requested model string, no cache split) — spec §6.
PIN_STRONG = "strong"
PIN_SERIES = "series"


class TrialStatus(enum.StrEnum):
    """Trial-level outcome.

    - ``COMPLETED`` — the trial produced a scored result view (the workspace is
      ready for the verifier, §7).
    - ``ERRORED`` — a task-level failure (nonzero engine exit, timeout, or an
      adapter error): scored as errored, recorded in the ledger as such.
    - ``INFRASTRUCTURE`` — auth failure or subscription usage-limit (§5/§6): not
      scored, not an error-retry burn; the matrix stops cleanly (§10).
    """

    COMPLETED = "completed"
    ERRORED = "errored"
    INFRASTRUCTURE = "infrastructure"


@dataclasses.dataclass
class TrialResult:
    """Outcome of one trial: 1..N run records plus the trial-level verdict.

    ``runs`` holds one :class:`~fathom.adapters.base.RunRecord` per model spawn —
    exactly one for a single-session trial, one per matching ``SUBAGENT_COMPLETE``
    event for a series trial.  ``wall_clock_s`` is the trial's own wall-clock
    (the engine's, for a series), distinct from the summed per-spawn durations.
    ``pin_level`` is :data:`PIN_STRONG` or :data:`PIN_SERIES`.  ``detail`` is a
    short human-readable note (timeout, infra signature, engine exit code).
    """

    status: TrialStatus
    runs: list[RunRecord]
    pin_level: str
    wall_clock_s: float = 0.0
    detail: str = ""

    @property
    def is_infrastructure(self) -> bool:
        """True when this trial must not be scored and must stop the matrix (§10)."""
        return self.status is TrialStatus.INFRASTRUCTURE

    @property
    def scored(self) -> bool:
        """True when the trial should feed the verifier (completed or task-errored)."""
        return self.status is not TrialStatus.INFRASTRUCTURE


@runtime_checkable
class StrategyExecutor(Protocol):
    """How a scenario turns one task into model spawns (spec §6).

    ``run_trial`` runs ``task`` in the already-staged ``workspace`` (a git repo on
    the task's pinned base branch, §3) under the resolved ``scenario``.  The
    ``runner`` is the vendor-abstract model-call boundary (ADR-0001): the
    single-session executor calls it directly; the series executor drives the
    engine, which is the one sanctioned non-adapter model-call path and so does
    not use ``runner``.  Inputs carry no scenario *identity* beyond the resolved
    transport pins the scenario already holds — grading stays blind (ADR-0003).
    """

    def run_trial(
        self,
        task: Task,
        workspace: Path,
        scenario: ResolvedScenario,
        runner: Runner,
    ) -> TrialResult:
        """Run ``task`` in ``workspace`` under ``scenario``; return a TrialResult."""
        ...
