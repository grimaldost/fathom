"""Reprompt-session strategy: one implementation spawn + one UNCONDITIONAL generic
re-verify/fix spawn -- the iteration-matched control for the gated arms (FM-6).

The gated arms give the agent extra spawns (a fix loop) that the bare single-session
arm never gets, so a bare-vs-gate lift confounds "gate discipline" with "simply more
attempts." This strategy gives the SAME extra spawn but with NO gate information: a
generic "re-examine and fix" prompt run unconditionally (not triggered by a red gate).
Comparing reprompt vs gated isolates the gate's INFORMATION + conditional forcing from
the mere extra iteration.

Stdlib only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fathom.adapters.base import ExitStatus
from fathom.strategies.base import PIN_STRONG, TrialResult, TrialStatus

if TYPE_CHECKING:
    from pathlib import Path

    from fathom.adapters.base import RunRecord, Runner
    from fathom.scenario import ResolvedScenario
    from fathom.taskbank import Task

_REPROMPT = (
    "Re-examine your implementation for correctness and completeness against the "
    "original task. Fix anything that is wrong, missing, or incompletely handled. "
    "Do not modify the tests."
)


class RepromptSessionExecutor:
    """One implementation spawn + one unconditional generic re-verify spawn.

    Iteration-matched control for the gated arms (FM-6): same extra spawn budget, but
    no gate information. Satisfies :class:`~fathom.strategies.base.StrategyExecutor`.
    """

    def run_trial(
        self,
        task: Task,
        workspace: Path,
        scenario: ResolvedScenario,
        runner: Runner,
    ) -> TrialResult:
        max_turns = task.limits.get("max_turns")
        runs: list[RunRecord] = []

        impl = runner.execute(task.instruction, workspace, scenario, max_turns=max_turns)
        runs.append(impl)
        if impl.status is ExitStatus.INFRASTRUCTURE:
            return self._infra(runs)

        # Unconditional second attempt -- no gate command, no test output injected.
        second = runner.execute(_REPROMPT, workspace, scenario, max_turns=max_turns)
        runs.append(second)
        if second.status is ExitStatus.INFRASTRUCTURE:
            return self._infra(runs)

        status = (
            TrialStatus.ERRORED
            if impl.status in (ExitStatus.ERROR, ExitStatus.TIMEOUT)
            else TrialStatus.COMPLETED
        )
        return TrialResult(
            status=status,
            runs=runs,
            pin_level=PIN_STRONG,
            wall_clock_s=sum(r.duration_s for r in runs),
            detail="reprompt (iteration-matched, no gate)",
        )

    @staticmethod
    def _infra(runs: list[RunRecord]) -> TrialResult:
        return TrialResult(
            status=TrialStatus.INFRASTRUCTURE,
            runs=runs,
            pin_level=PIN_STRONG,
            wall_clock_s=sum(r.duration_s for r in runs),
            detail="infrastructure",
        )
