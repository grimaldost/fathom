"""Prove a bank's criteria can FAIL — the naive-fix reference check.

``fathom validate`` proves a bank is *satisfiable* (the reference solution passes)
and *non-ceilinged* (the untouched fixture leaves a criterion false).  Neither
property proves the criteria are hard to satisfy.  ``e1-data`` passed both and
still collapsed to one discriminating trial per arm, because the fix a competent
agent reaches for first happened to satisfy every criterion; the v3 and v4 harder
banks ceilinged the same way at 0/180 correctness failures.

This check closes that gap.  A task declares, in ``task.toml``::

    [naive]
    must_pass = ["reconciliation_covers_all_periods"]
    must_fail = ["both_producers_reconciled"]

and ships the overlay it describes in ``<task>/refs/naive/``.  The overlay is
copied over a staged fixture, the verifier is run, and the declared contract is
enforced: the naive fix must satisfy the easy criteria and must NOT satisfy the
discriminating ones.  A task whose naive overlay passes its subtle criterion is
not a trap and is re-authored before the bank is run.

A task that declares no ``[naive]`` table is ``UNVERIFIABLE`` — reported, and
blocking under ``--strict``.  Calling an unmeasured property green is the
vacuous-gate failure this file exists to remove.

**What a PASS here is, and is not.**  The overlay in ``refs/naive/`` and the
``[naive]`` contract it is scored against are written by the same bank author in
the same commit, and no agent is spawned.  So a PASS is a *self-consistency*
property — this author's idea of the first-pass fix misses this author's declared
subtle criterion.  It bounds **one** easy path; it does not bound *the* easy path,
and it observes no behaviour.  In particular it inherits the blind spot
``src/fathom/validate.py`` names about its own triad: it does NOT catch a bank
whose tasks are simply too easy, so every arm succeeds.  Only the bare arm's
measured failure rate closes that, which is what a ``--repeats 1`` pilot with a
saturation gate is for.  Do not write "N tasks re-confirm they discriminate" from
this tool's output; write "N tasks' naive overlays honour their declared
contract".

Free — no spawn, no spend.

    python tools/check_naive_refs.py <bank> [--strict] [--tasks-dir tasks]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fathom.grading.verifier import run_verifier  # noqa: E402
from fathom.taskbank import Bank, Task, load_bank, stage_task  # noqa: E402

NAIVE_DIRNAME = "refs/naive"

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_UNVERIFIABLE = "unverifiable"
# A declared control is not a trap and must never be counted as one. It used to
# return STATUS_PASS, so the summary line reported one more discriminating task
# than the bank has -- and two documents carried the inflated count.
STATUS_CONTROL = "control"

EXIT_OK = 0
EXIT_INVALID = 3


@dataclass(frozen=True)
class NaiveCheck:
    task_id: str
    status: str
    detail: str


def overlay_naive(task: Task, workspace: Path) -> bool:
    """Copy ``<task>/refs/naive/`` over *workspace*; True when the overlay existed."""
    naive = task.task_dir / "refs" / "naive"
    if not naive.is_dir():
        return False
    shutil.copytree(naive, workspace, dirs_exist_ok=True)
    return True


def _declared(task: Task) -> tuple[list[str], list[str], bool] | None:
    """The task's [naive] contract, read from its own task.toml.

    `[naive]` is a bank-authoring table the harness core does not model, so it is
    read here rather than through `Task` — `taskbank` parses only the keys the
    runner needs.
    """
    try:
        with (task.task_dir / "task.toml").open("rb") as fh:
            naive = tomllib.load(fh).get("naive")
    except (OSError, tomllib.TOMLDecodeError):
        return None
    if not isinstance(naive, dict):
        return None
    must_pass = [str(c) for c in naive.get("must_pass", [])]
    must_fail = [str(c) for c in naive.get("must_fail", [])]
    control = bool(naive.get("control", False))
    # A control task carries no trap by design, so an empty must_fail is the
    # declaration rather than an omission -- but only when it says so out loud.
    if not must_fail and not (control and must_pass):
        return None
    return must_pass, must_fail, control


def check_task(task: Task, *, base_branch: str = "main") -> NaiveCheck:
    """Run the verifier against the task's naive overlay and score the contract."""
    declared = _declared(task)
    if declared is None:
        return NaiveCheck(
            task.id,
            STATUS_UNVERIFIABLE,
            "no [naive] must_fail declaration: nothing states which criterion a "
            "first-pass fix is supposed to MISS, so this task is not known to discriminate",
        )
    must_pass, must_fail, control = declared

    entry = task.task_dir / task.verify["entry"]
    timeout_s = int(task.verify.get("timeout_s", 60))

    try:
        with stage_task(task, base_branch) as workspace:
            if not overlay_naive(task, workspace):
                return NaiveCheck(
                    task.id,
                    STATUS_UNVERIFIABLE,
                    f"[naive] is declared but {NAIVE_DIRNAME}/ does not exist",
                )
            result = run_verifier(entry, workspace, timeout_s=timeout_s)
    except Exception as exc:  # noqa: BLE001 - a staging failure is a check failure
        return NaiveCheck(task.id, STATUS_FAIL, f"could not stage: {type(exc).__name__}: {exc}")

    criteria = result.criteria
    if result.outcome == "error" or criteria is None:
        return NaiveCheck(
            task.id,
            STATUS_FAIL,
            f"the verifier errored on the naive overlay: {(result.stderr or '')[:200]}",
        )

    missing = [c for c in (*must_pass, *must_fail) if c not in criteria]
    if missing:
        return NaiveCheck(
            task.id,
            STATUS_FAIL,
            f"[naive] names criteria the verifier does not emit: {missing}",
        )

    not_passed = [c for c in must_pass if not criteria[c]]
    not_failed = [c for c in must_fail if criteria[c]]

    if not_failed:
        return NaiveCheck(
            task.id,
            STATUS_FAIL,
            f"the naive fix SATISFIES {not_failed}: this task is not a trap. A first-pass "
            "fix already scores the discriminating criterion, so no arm can be told apart "
            "on it. Re-author the task before spending.",
        )
    if not_passed:
        return NaiveCheck(
            task.id,
            STATUS_FAIL,
            f"the naive fix does not satisfy {not_passed}: the overlay is not the fix a "
            "first pass reaches for (it is too weak), so it does not bound the easy path.",
        )
    if control:
        return NaiveCheck(
            task.id,
            STATUS_CONTROL,
            f"declared CONTROL: the obvious fix satisfies {must_pass}, by design. This task "
            "is not asked to discriminate; it is what makes the other tasks' numbers "
            "interpretable and where an arm that costs more than it buys becomes visible.",
        )
    return NaiveCheck(
        task.id,
        STATUS_PASS,
        f"naive fix passes {must_pass or '[]'} and misses {must_fail}: the task discriminates",
    )


def check_bank(bank: Bank, *, base_branch: str = "main") -> list[NaiveCheck]:
    return [check_task(task, base_branch=base_branch) for task in bank.tasks]


def checks_ok(checks: Sequence[NaiveCheck], *, strict: bool = False) -> bool:
    blocking = {STATUS_FAIL} | ({STATUS_UNVERIFIABLE} if strict else set())
    return not any(c.status in blocking for c in checks)


def render(bank_name: str, checks: Sequence[NaiveCheck]) -> str:
    marks = {
        STATUS_PASS: "PASS",
        STATUS_FAIL: "FAIL",
        STATUS_UNVERIFIABLE: "UNVERIFIABLE",
        STATUS_CONTROL: "CONTROL",
    }
    lines = [f"naive-refs: {bank_name}"]
    for check in checks:
        lines.append(f"  [{marks.get(check.status, check.status)}] {check.task_id}")
        lines.append(f"         {check.detail}")
    failed = sum(1 for c in checks if c.status == STATUS_FAIL)
    unver = sum(1 for c in checks if c.status == STATUS_UNVERIFIABLE)
    passed = sum(1 for c in checks if c.status == STATUS_PASS)
    controls = sum(1 for c in checks if c.status == STATUS_CONTROL)
    lines.append("")
    lines.append(
        f"NAIVE-REFS: {passed} discriminate, {controls} control, {failed} fail, "
        f"{unver} unverifiable" + ("  -- BANK CANNOT DISCRIMINATE" if failed else "")
    )
    lines.append(
        "  (a self-consistency property: the overlay and the contract it is checked "
        "against are authored together, and no agent behaviour is observed)"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bank")
    parser.add_argument("--tasks-dir", default="tasks")
    parser.add_argument("--strict", action="store_true", help="treat UNVERIFIABLE as blocking")
    args = parser.parse_args(argv)

    bank = load_bank(Path(args.tasks_dir) / args.bank)
    checks = check_bank(bank)
    print(render(bank.name, checks))
    return EXIT_OK if checks_ok(checks, strict=args.strict) else EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
