"""Bank validation — the rule that decides whether a bank can measure anything.

CONTRIBUTING stated the validation triad in prose.  A rule that must always hold
belongs in a gate, and this one has already failed twice at real cost:

* ``ablation-v1`` was quality-null **by instrument** — a greenfield task left no
  regression surface, so nothing the arms did could show up as a difference.
* the v3 and v4 harder banks both ceilinged with 0/180 correctness failures at
  n=45, discovered after the spend rather than before it.

The triad, and what each property protects against:

1. :data:`PROP_FIXTURE_FAILS` — **the unmodified fixture must leave the arm
   something to do**: at least one verifier criterion starts false.  This is the
   anti-ceiling property and the answer to "does the bare arm ever actually
   fail?".  A fixture on which every criterion is already true scores every arm
   100%, and the run returns a null that reads as "the tool does not help" —
   precisely the answer the decisions downstream of this harness are hoping for.
   Read the CRITERIA, not the exit code: a verifier may legitimately gate exit 0
   on a preservation criterion that holds before the agent starts, while the
   signal being measured lives in the criteria that do not.  Always checked.

   What this property does NOT catch: a bank whose tasks are simply too EASY, so
   every arm succeeds.  That ceiling is invisible before the spend and stays
   authoring judgement (discrimination ratio, turn budget, discriminate-by-scale)
   in the authoring reference.
2. :data:`PROP_SOLUTION_PASSES` — **the verifier must PASS on a reference
   solution** (``<task>/solution/`` overlaid on the fixture).  Guards the mirror
   failure: an unsatisfiable verifier no arm can ever satisfy.
3. :data:`PROP_GATE_RUNNABLE` — **the task's gate command must actually run on
   the untouched fixture.**  Deliberately weaker than "must be green", because
   green is not the universally correct answer: a brownfield task whose visible
   suite encodes the target feature (``ablation-v2``) starts red BY DESIGN, and
   that red is the signal a gated arm works against.  The harness cannot tell a
   deliberate red baseline from a broken one, so it refuses only when the gate
   could not execute at all (command not found) and reports the observed colour
   otherwise as a WARN the author must confirm.

Properties 2 and 3 are ``unverifiable`` when the bank ships no reference solution
or declares no gate.  ``unverifiable`` is deliberately NOT a pass: it is reported
as its own status and blocks under ``--strict``.  Calling an unmeasurable
property green is the vacuous-gate failure mode this module exists to remove —
and so is refusing a bank the harness merely cannot interpret, which is why the
ambiguous red-gate case is ``warn`` rather than ``fail``.

What stays out: the discrimination ratio, the measured turn budget and the
discriminate-by-scale judgement are authoring judgement, not machine checks, and
live in the authoring reference.

Free — every check runs the verifier locally against a staged fixture.  No spawn,
no spend.
"""

from __future__ import annotations

import dataclasses
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from fathom.taskbank import Bank, Task

PROP_FIXTURE_FAILS = "verifier fails on the unmodified fixture"
PROP_SOLUTION_PASSES = "verifier passes on the reference solution"
PROP_GATE_RUNNABLE = "task gate is runnable on the fixture"

# Where a bank ships the reference implementation, as an overlay copied over the
# staged fixture tree (the convention ablation-v1 and ablation-v2 already use).
SOLUTION_DIRNAME = "solution"

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_WARN = "warn"  # observed, ambiguous, reported — blocks only under --strict
STATUS_UNVERIFIABLE = "unverifiable"

# A shell reporting "command not found" — the gate never ran at all, which is a
# broken bank rather than a red baseline.
_UNRUNNABLE_RCS = (127, 9009)

_GATE_TIMEOUT_S = 300


@dataclasses.dataclass(frozen=True)
class BankCheck:
    """One property, checked against one task."""

    task_id: str
    prop: str
    status: str  # pass | fail | unverifiable
    detail: str = ""


def overlay_solution(task: Task, workspace: Path) -> bool:
    """Copy ``<task>/solution/`` over *workspace*; True when a solution existed."""
    solution = task.task_dir / SOLUTION_DIRNAME
    if not solution.is_dir():
        return False
    shutil.copytree(solution, workspace, dirs_exist_ok=True)
    return True


def run_gate(command: str, workspace: Path) -> tuple[int, str]:
    """Run a task's gate command from *workspace*; return (returncode, output)."""
    proc = subprocess.run(  # noqa: S602 - the command is bank-authored, not user input
        command,
        shell=True,
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=_GATE_TIMEOUT_S,
        errors="replace",
    )
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or ""))[-2000:]


def validate_bank(
    bank: Bank,
    *,
    stage_fn: Callable[..., Any],
    verifier_fn: Callable[..., Any],
    gate_fn: Callable[[str, Path], tuple[int, str]] = run_gate,
    overlay_fn: Callable[[Task, Path], bool] = overlay_solution,
    base_branch: str = "main",
) -> list[BankCheck]:
    """Check the validation triad for every task in *bank*.

    Seams are injected so the logic is unit-testable without git, a subprocess or
    a real verifier — the same split the smoke gate uses.
    """
    checks: list[BankCheck] = []

    if not bank.tasks:
        return [
            BankCheck(
                "(bank)",
                PROP_FIXTURE_FAILS,
                STATUS_FAIL,
                "the bank declares no tasks — an empty bank measures nothing, and "
                "vacuously passing it would be the failure this check exists to catch",
            )
        ]

    for task in bank.tasks:
        checks.extend(_check_task(task, stage_fn, verifier_fn, gate_fn, overlay_fn, base_branch))
    return checks


def _fixture_check(task: Task, result: Any) -> BankCheck:
    """Property 1: does the untouched fixture leave the arm something to do?

    Read the CRITERIA, not just the exit code.  A verifier legitimately gates
    exit 0 on a preservation criterion that is trivially true before the agent
    touches anything (``behavior_preserved``) while the signal being measured
    lives in the other criteria.  ``skill-pyeng-v1`` is exactly that shape — its
    scorecard shows the strongest discrimination in the corpus (bare 0/2,
    pyeng-skill 3/3) — and an exit-code-only check reported it as unmeasurable.
    A gate that blocks the reference bank is a gate the operator learns to skip.
    """
    outcome = getattr(result, "outcome", "error")
    criteria = getattr(result, "criteria", None)

    if outcome == "error":
        return BankCheck(
            task.id,
            PROP_FIXTURE_FAILS,
            STATUS_FAIL,
            "the verifier errored on the unmodified fixture (crash, timeout or "
            f"non-JSON): {(getattr(result, 'stderr', '') or '')[:200]}",
        )

    if not criteria:
        return BankCheck(
            task.id,
            PROP_FIXTURE_FAILS,
            STATUS_FAIL,
            "the verifier emitted no criteria on the unmodified fixture — there is "
            "nothing for the per-criterion table to report and nothing to discriminate on",
        )

    start_false = sorted(k for k, v in criteria.items() if not v)
    if start_false:
        return BankCheck(
            task.id,
            PROP_FIXTURE_FAILS,
            STATUS_PASS,
            f"{len(start_false)}/{len(criteria)} criteria start false, so an arm has "
            f"something to fix: {start_false}"
            + (
                ""
                if outcome == "fail"
                else " (the exit-code gate is already green — the "
                "discriminating signal is per-criterion, not headline pass-rate)"
            ),
        )

    return BankCheck(
        task.id,
        PROP_FIXTURE_FAILS,
        STATUS_FAIL,
        f"every criterion ({sorted(criteria)}) is ALREADY TRUE on the unmodified "
        "fixture — this task cannot discriminate between arms and will score every arm 100%",
    )


def _gate_check(task: Task, gate_cmd: str, rc: int, output: str) -> BankCheck:
    """Property 3, scoped to what the harness can actually tell apart."""
    if rc == 0:
        return BankCheck(
            task.id, PROP_GATE_RUNNABLE, STATUS_PASS, f"`{gate_cmd}` exited 0 (green baseline)"
        )
    if rc in _UNRUNNABLE_RCS:
        return BankCheck(
            task.id,
            PROP_GATE_RUNNABLE,
            STATUS_FAIL,
            f"`{gate_cmd}` exited {rc} — the gate command could not be executed at all, "
            f"so every gated arm's gate is meaningless: {output[-400:]}",
        )
    return BankCheck(
        task.id,
        PROP_GATE_RUNNABLE,
        STATUS_WARN,
        f"`{gate_cmd}` exited {rc} — the baseline is RED. Deliberate for a brownfield "
        "task whose visible suite encodes the target feature; a defect if the fixture "
        f"is simply broken. Confirm which: {output[-300:]}",
    )


def _check_task(
    task: Task,
    stage_fn: Callable[..., Any],
    verifier_fn: Callable[..., Any],
    gate_fn: Callable[[str, Path], tuple[int, str]],
    overlay_fn: Callable[[Task, Path], bool],
    base_branch: str,
) -> list[BankCheck]:
    entry = task.task_dir / task.verify["entry"]
    timeout_s = int(task.verify.get("timeout_s", 60))
    checks: list[BankCheck] = []

    # --- 1. the verifier must FAIL on the untouched fixture ----------------
    try:
        with stage_fn(task, base_branch) as workspace:
            checks.append(_fixture_check(task, verifier_fn(entry, workspace, timeout_s=timeout_s)))

            # --- 3. the task's gate must be green on that same fixture -----
            gate_cmd = task.gate.get("run")
            if not gate_cmd:
                checks.append(
                    BankCheck(
                        task.id,
                        PROP_GATE_RUNNABLE,
                        STATUS_UNVERIFIABLE,
                        "the task declares no [gate] run command",
                    )
                )
            else:
                checks.append(_gate_check(task, str(gate_cmd), *gate_fn(str(gate_cmd), workspace)))
    except Exception as exc:  # noqa: BLE001 - a staging failure is a validation failure
        return [
            BankCheck(
                task.id,
                PROP_FIXTURE_FAILS,
                STATUS_FAIL,
                f"could not stage the task: {type(exc).__name__}: {exc}",
            )
        ]

    # --- 2. the verifier must PASS on the reference solution ---------------
    try:
        with stage_fn(task, base_branch) as workspace:
            if not overlay_fn(task, workspace):
                checks.append(
                    BankCheck(
                        task.id,
                        PROP_SOLUTION_PASSES,
                        STATUS_UNVERIFIABLE,
                        f"no {SOLUTION_DIRNAME}/ directory — the verifier is not known to be "
                        "satisfiable, so a null result from this task cannot be distinguished "
                        "from an unsatisfiable verifier",
                    )
                )
            else:
                result = verifier_fn(entry, workspace, timeout_s=timeout_s)
                outcome = getattr(result, "outcome", "error")
                checks.append(
                    BankCheck(
                        task.id,
                        PROP_SOLUTION_PASSES,
                        STATUS_PASS if outcome == "pass" else STATUS_FAIL,
                        f"verifier outcome on {SOLUTION_DIRNAME}/ = {outcome}"
                        + (
                            ""
                            if outcome == "pass"
                            else " — the reference implementation does not satisfy the verifier, "
                            "so NO arm can; every result this task produces is a manufactured null"
                        ),
                    )
                )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            BankCheck(
                task.id,
                PROP_SOLUTION_PASSES,
                STATUS_FAIL,
                f"could not check the reference solution: {type(exc).__name__}: {exc}",
            )
        )

    return checks


def validation_ok(checks: Sequence[BankCheck], *, strict: bool = False) -> bool:
    """True when no check FAILED (and, under *strict*, none warned or was unverifiable)."""
    blocking = {STATUS_FAIL} | ({STATUS_WARN, STATUS_UNVERIFIABLE} if strict else set())
    return not any(c.status in blocking for c in checks)


def render_validation(bank_name: str, checks: Sequence[BankCheck]) -> str:
    """Human-readable validation report for one bank."""
    marks = {
        STATUS_PASS: "PASS",
        STATUS_FAIL: "FAIL",
        STATUS_WARN: "WARN",
        STATUS_UNVERIFIABLE: "UNVERIFIABLE",
    }
    lines = [f"validate: {bank_name}"]
    by_task: dict[str, list[BankCheck]] = {}
    for c in checks:
        by_task.setdefault(c.task_id, []).append(c)
    for task_id, task_checks in by_task.items():
        lines.append(f"  {task_id}:")
        for c in task_checks:
            lines.append(f"    [{marks.get(c.status, c.status)}] {c.prop}")
            if c.detail:
                lines.append(f"           {c.detail}")

    failed = sum(1 for c in checks if c.status == STATUS_FAIL)
    warned = sum(1 for c in checks if c.status == STATUS_WARN)
    unver = sum(1 for c in checks if c.status == STATUS_UNVERIFIABLE)
    passed = sum(1 for c in checks if c.status == STATUS_PASS)
    lines.append("")
    lines.append(
        f"VALIDATION: {passed} pass, {failed} fail, {warned} warn, {unver} unverifiable"
        + ("  — BANK CANNOT MEASURE" if failed else "")
    )
    return "\n".join(lines)
