"""Gated-session strategy: one spawn + a deterministic gate + a bounded fix loop.

Models a series engine's engine-INDEPENDENT gate discipline WITHOUT the
orchestration engine: the agent implements once, the harness runs the task's
visible gate command, and on failure re-prompts the agent with the gate output up
to ``max_fix_attempts`` times. The ``with_review`` variant adds one structured
review pass (VERDICT + feedback -> one fix) after the gate is green. Ablation
companion to ``single_session`` / ``series`` (spec 6).

The gate the agent runs is the task's OWN visible suite (``task.gate["run"]``),
distinct from the blind harness-side acceptance oracle (``verify.py``, ADR-0003)
that grades every arm afterward. ``detail`` records the gate outcome (first/final,
fix count) so the defect-escape metric is recoverable from the ledger.

Stdlib only.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from fathom.adapters.base import ExitStatus
from fathom.strategies.base import PIN_STRONG, TrialResult, TrialStatus

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from fathom.adapters.base import RunRecord, Runner
    from fathom.scenario import ResolvedScenario
    from fathom.taskbank import Task

_GATE_TIMEOUT_S = 120
_FIX_PROMPT = (
    "The project's quality gate is failing. Fix the implementation so the gate passes. "
    "Do not modify the tests.\n\nGate command: {cmd}\nGate output (tail):\n{output}"
)
_REVIEW_PROMPT = (
    "Review your implementation for correctness against the task. If it is complete and "
    "correct, reply with a line 'VERDICT: APPROVE'. Otherwise reply 'VERDICT: "
    "REQUEST_CHANGES' followed by the specific fixes needed."
)


class GatedSessionExecutor:
    """One spawn + deterministic gate + bounded fix loop (optional review pass).

    Satisfies :class:`~fathom.strategies.base.StrategyExecutor`. ``task.gate["run"]``
    is the visible gate command; a task that defines no gate degrades to a single
    spawn (such a task should use ``single-session`` instead).
    """

    def __init__(
        self,
        max_fix_attempts: int = 2,
        with_review: bool = False,
        extra_gate_cmds: Sequence[str] = (),
    ) -> None:
        self.max_fix_attempts = max_fix_attempts
        self.with_review = with_review
        # Scenario-level gate augmentation (harness-side oracle strengthening):
        # commands run after the task's own gate, same red/green contract.
        self.extra_gate_cmds = tuple(extra_gate_cmds)

    def run_trial(
        self,
        task: Task,
        workspace: Path,
        scenario: ResolvedScenario,
        runner: Runner,
    ) -> TrialResult:
        max_turns = task.limits.get("max_turns")
        runs: list[RunRecord] = []
        gate_cmd = (getattr(task, "gate", None) or {}).get("run", "")
        gate_cmds = [c for c in (gate_cmd, *self.extra_gate_cmds) if c]

        impl = runner.execute(task.instruction, workspace, scenario, max_turns=max_turns)
        runs.append(impl)
        if impl.status is ExitStatus.INFRASTRUCTURE:
            return self._infra(runs)

        notes: list[str] = []
        gate_ok = True
        if gate_cmds:
            first_ok: bool | None = None
            for attempt in range(self.max_fix_attempts + 1):
                gate_ok, output = self._run_gates(gate_cmds, workspace)
                if first_ok is None:
                    first_ok = gate_ok
                if gate_ok or attempt == self.max_fix_attempts:
                    break
                fix = runner.execute(
                    _FIX_PROMPT.format(cmd=" && ".join(gate_cmds), output=output[-3000:]),
                    workspace,
                    scenario,
                    max_turns=max_turns,
                )
                runs.append(fix)
                if fix.status is ExitStatus.INFRASTRUCTURE:
                    return self._infra(runs)
            notes.append(
                f"gate first={'green' if first_ok else 'red'} "
                f"final={'green' if gate_ok else 'red'} fixes={len(runs) - 1}"
            )

        if self.with_review and gate_ok:
            rev = runner.execute(_REVIEW_PROMPT, workspace, scenario, max_turns=max_turns)
            runs.append(rev)
            if rev.status is ExitStatus.INFRASTRUCTURE:
                return self._infra(runs)
            if "REQUEST_CHANGES" in (rev.result_text or "").upper():
                fix = runner.execute(
                    "Apply the changes from the review, then ensure the gate still passes.",
                    workspace,
                    scenario,
                    max_turns=max_turns,
                )
                runs.append(fix)
                if fix.status is ExitStatus.INFRASTRUCTURE:
                    return self._infra(runs)
                notes.append("review=REQUEST_CHANGES")
            else:
                notes.append("review=APPROVE")

        # A gradeable result view always exists (the workspace); the blind verifier
        # scores it regardless of the gate verdict. Trial status reflects whether the
        # primary implementation spawn ran, not the gate outcome (gate-red is a
        # measured result, not a trial error).
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
            detail="; ".join(notes),
        )

    @classmethod
    def _run_gates(cls, cmds: Sequence[str], workspace: Path) -> tuple[bool, str]:
        """Run *cmds* in order; first red short-circuits.

        Returns ``(True, "")`` when every command exits 0, else ``(False, output)``
        where output identifies the failing command (the fix prompt quotes it).
        """
        for cmd in cmds:
            ok, output = cls._run_gate(cmd, workspace)
            if not ok:
                return False, f"$ {cmd}\n{output}"
        return True, ""

    @staticmethod
    def _run_gate(cmd: str, workspace: Path) -> tuple[bool, str]:
        try:
            proc = subprocess.run(
                cmd,
                shell=True,  # noqa: S602 - gate is a task-authored command (engine parity)
                cwd=str(workspace),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=_GATE_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return False, f"gate timed out after {_GATE_TIMEOUT_S}s"
        return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")

    @staticmethod
    def _infra(runs: list[RunRecord]) -> TrialResult:
        return TrialResult(
            status=TrialStatus.INFRASTRUCTURE,
            runs=runs,
            pin_level=PIN_STRONG,
            wall_clock_s=sum(r.duration_s for r in runs),
            detail="infrastructure",
        )
