"""Single-session strategy executor: exactly one Runner call per trial.

The bare-agent and single-long-session arms differ only in their scenario pins
(model, effort, limits) and the adapter's allow/disallow lists — both make one
spawn.  This executor is that one spawn: it hands the task instruction to the
Runner and wraps the resulting :class:`~fathom.adapters.base.RunRecord` in a
:class:`TrialResult` with the strong pin level (spec §6).

Stdlib only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fathom.adapters.base import ExitStatus
from fathom.strategies.base import PIN_STRONG, TrialResult, TrialStatus

if TYPE_CHECKING:
    from pathlib import Path

    from fathom.adapters.base import Runner
    from fathom.scenario import ResolvedScenario
    from fathom.taskbank import Task

# Map one spawn's outcome to the trial-level verdict.  A timeout is the run's own
# failure (scored as errored, §5); auth / usage-limit is infrastructure and stops
# the matrix cleanly without scoring (§10).
_STATUS_MAP: dict[ExitStatus, TrialStatus] = {
    ExitStatus.OK: TrialStatus.COMPLETED,
    ExitStatus.ERROR: TrialStatus.ERRORED,
    ExitStatus.TIMEOUT: TrialStatus.ERRORED,
    ExitStatus.INFRASTRUCTURE: TrialStatus.INFRASTRUCTURE,
}


class SingleSessionExecutor:
    """One Runner spawn per trial (spec §6).

    Satisfies the :class:`~fathom.strategies.base.StrategyExecutor` protocol.  Holds
    no per-arm configuration: the model/effort/limits live on the resolved
    scenario and the allow/disallow lists live on the ``runner`` (an adapter-level
    isolation property, ADR-0004), so the same executor instance drives both the
    bare and single-long-session arms.
    """

    def run_trial(
        self,
        task: Task,
        workspace: Path,
        scenario: ResolvedScenario,
        runner: Runner,
    ) -> TrialResult:
        """Run ``task.instruction`` once through ``runner``; return a TrialResult.

        Exactly one ``runner.execute`` call is made — the defining property of
        the single-session arm.
        """
        record = runner.execute(
            task.instruction, workspace, scenario, max_turns=task.limits.get("max_turns")
        )
        status = _STATUS_MAP.get(record.status, TrialStatus.ERRORED)
        detail = "" if status is TrialStatus.COMPLETED else (record.result_text or "")[:200]
        return TrialResult(
            status=status,
            runs=[record],
            pin_level=PIN_STRONG,
            wall_clock_s=record.duration_s,
            detail=detail,
        )
