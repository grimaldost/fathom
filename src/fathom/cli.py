"""CLI entry point — fathom run / report / smoke (spec §10)."""

from __future__ import annotations

import argparse
import json
import dataclasses
import os
import pathlib
import sys
import tomllib
from collections.abc import Sequence
from typing import Any, Callable, TextIO

import fathom.arming as _arming
import fathom.ledger as _ledger
from fathom.grading.verifier import run_verifier
from fathom.scenario import ResolvedScenario
from fathom.taskbank import (
    Bank,
    Task,
    fixture_drift,
    fixture_fingerprint,
    fixture_manifest,
    load_bank,
    stage_task,
)

_DEFAULT_REPEATS = 2
_DEFAULT_BASE_BRANCH = "main"
# The adapter's own per-spawn cap (ClaudeCliRunner.default_max_budget_usd). Mirrored
# here so the plan's ceiling is computed from the cap that will actually bound the
# spawns when --max-budget-usd is not given; test_cli_budget asserts the two agree.
_DEFAULT_SPAWN_BUDGET_USD = 5.00
_SERIES_TEMPLATE_NAME = "series.toml"
# The engine's own default when a series template omits [review]; mirrors
# GatedSessionExecutor's repair budget.
_SERIES_DEFAULT_MAX_FIX_ATTEMPTS = 2
# Bound on the verifier output persisted per trial (FATH-B14). The ledger is
# committed, so this is the line between "diagnosable" and "a megabyte of agent
# output in git history on one bad trial".
_VERIFIER_OUTPUT_CAP = 4096
SCENARIOS_DIR = pathlib.Path("scenarios")
TASKS_DIR = pathlib.Path("tasks")

# Named exit codes (spec §10)
EXIT_OK = 0
EXIT_INFRASTRUCTURE = 10
EXIT_UNARMED = 11  # a treatment arm could not be proven armed (FATH-B01)
EXIT_BANK_INVALID = 12  # the bank cannot discriminate between arms (FATH-B02)
EXIT_UNRECONCILED = 13  # two derivations of one fact disagree (FATH-B62/B63)
EXIT_RUN_BUDGET = 14  # the per-invocation spend rail halted the matrix (FATH-B04)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fathom",
        description="Scenario-blind tool-effectiveness evals",
    )
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute the scenario matrix against a task bank")
    run_p.add_argument("bank", help="Bank name (tasks/<bank>/ directory)")
    run_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan + ceiling; spawn nothing",
    )
    run_p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap planned trials to N",
    )
    run_p.add_argument(
        "--tasks",
        default=None,
        metavar="ID[,ID...]",
        help="Run only these task ids. The way to buy a SCREEN before the full matrix "
        "(e.g. one band, or the positive control, at higher repeats). --limit cannot do "
        "it: the plan is scenario-major, so --limit cuts whole arms off the end. Unknown "
        "ids are an error, never a silent empty run.",
    )
    run_p.add_argument(
        "--repeats",
        type=int,
        default=_DEFAULT_REPEATS,
        help=f"Repeats per (scenario, task) pair (default: {_DEFAULT_REPEATS})",
    )
    run_p.add_argument(
        "--scenarios-dir",
        type=pathlib.Path,
        default=SCENARIOS_DIR,
        dest="scenarios_dir",
        metavar="DIR",
        help="Directory globbed (non-recursively) for arm *.toml (default: scenarios/). "
        "REQUIRED for a bank that ships its own arms in a subdir, or the wrong arms run.",
    )
    run_p.add_argument(
        "--tasks-dir",
        type=pathlib.Path,
        default=TASKS_DIR,
        dest="tasks_dir",
        metavar="DIR",
        help="Directory holding <bank>/ task banks (default: tasks/).",
    )
    run_p.add_argument(
        "--ledger-dir",
        type=pathlib.Path,
        default=None,
        dest="ledger_dir",
        metavar="DIR",
        help="Directory for the append-only <bank>.jsonl ledger (default: ledger/).",
    )
    run_p.add_argument(
        "--include-holdout",
        action="store_true",
        dest="include_holdout",
        help="Also run the bank's sealed holdout tasks (ADR-0005). The auditable way to "
        "spend a holdout for a promotion decision — trials are marked holdout in the ledger.",
    )
    run_p.add_argument(
        "--max-spawn-usd",
        type=float,
        default=None,
        dest="max_spawn_usd",
        metavar="USD",
        help="PER-SPAWN budget cap (overrides the adapter default of 5.0). A value above "
        "the default LOOSENS the only runaway guard there is; the printed ceiling is "
        "trials x this cap, so the plan shows what it really buys. For a cap on what the "
        "whole invocation may spend, use --max-run-usd.",
    )
    run_p.add_argument(
        # The original spelling. It is kept working permanently, not deprecated on a
        # timer: it appears in eleven published reports (which record what was actually
        # run and must not be rewritten) and inside mounted plugin trees whose bytes are
        # hashed into config_hash, where an edit would fork a committed ledger's resume
        # key. Renaming the flag is cheap; renaming the string everywhere is not.
        "--max-budget-usd",
        type=float,
        default=None,
        dest="legacy_max_budget_usd",
        metavar="USD",
        help="Deprecated spelling of --max-spawn-usd (still honoured; it was never a run "
        "total, which is what the name kept implying).",
    )
    run_p.add_argument(
        "--max-run-usd",
        type=float,
        default=None,
        dest="max_run_usd",
        metavar="USD",
        help="Halt this INVOCATION once its own spend reaches USD. Checked between trials "
        "from the costs this process has observed — never summed from the ledger, which "
        "holds every prior invocation of a resumable matrix and would trip at $0 of new "
        "spend on a resume. Because a trial's cost is only known once it is paid, the "
        "realised total can exceed the rail by the last trial's own ceiling (up to "
        "n_prs x (1 impl + fixes) spawns on a series arm). Resuming is safe: the ledger is "
        "the checkpoint, so a halt costs nothing already bought.",
    )

    run_p.add_argument(
        "--skip-bank-validation",
        action="store_true",
        dest="skip_bank_validation",
        help="Spend WITHOUT checking that the bank can discriminate. The check is "
        "free and two banks have already ceilinged at 0/180 correctness failures "
        "after the spend; skip it only when re-running a bank validated this session.",
    )
    run_p.add_argument(
        "--skip-arming-check",
        action="store_true",
        dest="skip_arming_check",
        help="Spend WITHOUT proving the treatment arms are armed. The arming gate "
        "costs a fraction of a cent per arm and exists because an entirely unarmed "
        "arm once scored 100%% over 9 trials; skip it only to re-run a matrix whose "
        "arming was already verified this session.",
    )

    void_p = sub.add_parser(
        "void",
        help=(
            "Append a void row excluding one recorded trial (and its run rows) from every "
            "reader; the trial is re-run on resume. Append-only: nothing is rewritten."
        ),
    )
    void_p.add_argument("bank")
    void_p.add_argument("--scenario", required=True, help="arm name as recorded on the trial row")
    void_p.add_argument("--repeat", required=True, type=int)
    void_p.add_argument("--task-id", default=None, help="defaults to the bank's only task")
    void_p.add_argument("--reason", required=True, help="the instrument defect, one sentence")
    void_p.add_argument("--evidence", default="", help="where a reader can verify it")
    void_p.add_argument("--ledger-dir", default=None)

    report_p = sub.add_parser("report", help="Render a scorecard from the ledger")
    report_p.add_argument("bank", help="Bank name")

    val_p = sub.add_parser(
        "validate",
        help="Check the bank-validation triad before any spend (free — no spawns)",
    )
    val_p.add_argument("bank", help="Bank name (tasks/<bank>/ directory)")
    val_p.add_argument(
        "--tasks-dir",
        type=pathlib.Path,
        default=TASKS_DIR,
        dest="tasks_dir",
        metavar="DIR",
        help="Directory holding <bank>/ task banks (default: tasks/).",
    )
    val_p.add_argument(
        "--strict",
        action="store_true",
        help="Also fail on UNVERIFIABLE properties (no reference solution, no gate).",
    )

    arm_p = sub.add_parser(
        "verify-arming",
        help="Prove each treatment arm is actually armed on a real spawn (§FATH-B01)",
    )
    arm_p.add_argument(
        "--scenarios-dir",
        type=pathlib.Path,
        default=SCENARIOS_DIR,
        dest="scenarios_dir",
        metavar="DIR",
        help="Directory globbed (non-recursively) for arm *.toml (default: scenarios/).",
    )

    rec_p = sub.add_parser(
        "reconcile",
        help="Check every fact this repo derives twice (free — no spawns)",
    )
    rec_p.add_argument(
        "--check",
        action="append",
        dest="checks",
        metavar="NAME",
        help="Run only this reconciliation (repeatable). Default: all of them.",
    )
    rec_p.add_argument(
        "--list",
        action="store_true",
        dest="list_checks",
        help="List the registered reconciliations and exit",
    )
    smoke_p = sub.add_parser("smoke", help="Real-spawn isolation smoke gate (§11)")
    smoke_p.add_argument(
        "--force-fail",
        action="store_true",
        help="Append a forced failing check to demonstrate the nonzero exit path",
    )
    smoke_p.add_argument(
        "--no-engine-boundary",
        action="store_true",
        help="Skip the engine-boundary assertion (group 4)",
    )

    return p


def _series_spawn_plan(task: Task) -> tuple[int, int] | None:
    """`(n_prs, max_fix_attempts)` from a task's committed series template.

    Returns None when the template is absent or unreadable — the trial will fail at
    run time for the same reason, and the planner's job is to price, not to gate.
    """
    template = pathlib.Path(task.task_dir) / _SERIES_TEMPLATE_NAME
    try:
        with template.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    prs = data.get("prs")
    if not isinstance(prs, list) or not prs:
        return None
    review = data.get("review")
    attempts = _SERIES_DEFAULT_MAX_FIX_ATTEMPTS
    if isinstance(review, dict) and isinstance(review.get("max_fix_attempts"), int):
        attempts = review["max_fix_attempts"]
    return len(prs), max(0, attempts)


def _trial_ceiling_usd(
    scenario: ResolvedScenario, task: Task, max_budget_usd: float | None
) -> float:
    """Worst-case USD for ONE trial of `scenario` on `task`.

    Two corrections to a flat per-trial rate, both of which made the plan understate
    what a run could spend, and neither of which the other catches.

    **Spawns per trial.** One spawn per trial is true of every single-spawn strategy
    and false of `series`, which spends one implementation spawn plus up to
    `max_fix_attempts` fix spawns for EVERY PR in the task's decomposition, each
    against its own per-spawn cap. Pricing that at one spawn is not a conservative
    estimate — it is a bound the operator believes and the run exceeds by an order of
    magnitude, which is exactly what the upfront ceiling exists to prevent
    (spec §10 / C4).

    **The cap actually in force.** `--max-budget-usd` is PER-SPAWN, so passing a
    number larger than the adapter's default LOOSENS the only runaway guard there is.
    While the single-spawn price was a hardcoded constant, the plan printed the same
    reassuring total either way — which is how a 20x loosening once got written up as
    a $100 rail. Deriving it from the cap makes the flag's real effect visible in the
    plan, before the spend.
    """
    per_spawn = max_budget_usd if max_budget_usd is not None else _DEFAULT_SPAWN_BUDGET_USD
    if scenario.strategy != "series":
        return per_spawn
    plan = _series_spawn_plan(task)
    if plan is None:
        return per_spawn
    from fathom.strategies.series import DEFAULT_BUDGET_FIX, DEFAULT_BUDGET_IMPL

    n_prs, attempts = plan
    impl = max_budget_usd if max_budget_usd is not None else DEFAULT_BUDGET_IMPL
    fix = max_budget_usd if max_budget_usd is not None else DEFAULT_BUDGET_FIX
    return n_prs * (impl + attempts * fix)


def run_matrix(
    bank: Bank,
    resolved_scenarios: list[ResolvedScenario],
    repeats: int,
    *,
    executor_factory: Callable[[ResolvedScenario], Any] | None = None,
    runner_factory: Callable[[ResolvedScenario], Any] | None = None,
    stage_task_fn: Callable[[Task, str], Any] | None = None,
    verifier_fn: Callable[[pathlib.Path, pathlib.Path], Any] | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    task_ids: Sequence[str] | None = None,
    ledger_dir: pathlib.Path | None = None,
    max_budget_usd: float | None = None,
    max_run_usd: float | None = None,
    include_holdout: bool = False,
    arming_probe: Any | None = None,
    skip_arming_check: bool = False,
    skip_bank_validation: bool = False,
    out: TextIO | None = None,
) -> int:
    """Execute or plan a scenario matrix against a task bank.

    Prints the upfront trial/spawn counts and cost ceiling BEFORE any spawn
    (spec §10).  Returns EXIT_OK (0) or EXIT_INFRASTRUCTURE (10).

    An infrastructure error from any executor (auth / usage-limit) stops the
    matrix cleanly: the affected trial is not scored, the ledger is untouched
    as the resume checkpoint, and EXIT_INFRASTRUCTURE is returned.
    """
    _ledger_dir = ledger_dir if ledger_dir is not None else _ledger.LEDGER_DIR
    _out = out if out is not None else sys.stdout
    _stage_fn = stage_task_fn if stage_task_fn is not None else stage_task
    _verifier = verifier_fn if verifier_fn is not None else run_verifier

    # --- Build and filter the planned matrix ---
    # Holdouts are excluded by default (ADR-0005 sealing). --include-holdout is the
    # sanctioned, auditable way to spend one for a promotion decision — the trials it
    # produces carry holdout=True (below), so the report renders them in a separate
    # section and spending is visible, rather than requiring a bank.toml edit that is
    # indistinguishable from quietly unsealing.
    tasks_to_run = (
        bank.tasks if include_holdout else [t for t in bank.tasks if t.id not in bank.holdout]
    )
    # --tasks: buy a screen (one band, or the control, at higher repeats) before the
    # full matrix. Applied AFTER the holdout filter, so it can never unseal a holdout
    # by naming it — that still takes --include-holdout, which marks the ledger.
    if task_ids is not None:
        wanted = list(dict.fromkeys(task_ids))
        known = {t.id for t in bank.tasks}
        unknown = [t for t in wanted if t not in known]
        if unknown:
            print(
                f"ERROR: --tasks names id(s) not in bank '{bank.name}': {', '.join(unknown)}\n"
                f"known: {', '.join(sorted(known))}",
                file=sys.stderr,
            )
            return 1
        sealed = [t for t in wanted if t not in {task.id for task in tasks_to_run}]
        if sealed:
            print(
                f"ERROR: --tasks names sealed holdout task(s): {', '.join(sealed)}. "
                "Spending a holdout takes --include-holdout (ADR-0005), which marks the "
                "trials in the ledger.",
                file=sys.stderr,
            )
            return 1
        tasks_to_run = [t for t in tasks_to_run if t.id in set(wanted)]

    done = _ledger.completed_keys(bank.name, ledger_dir=_ledger_dir)

    all_tuples: list[tuple[ResolvedScenario, Task, int]] = [
        (sc, task, repeat)
        for sc in resolved_scenarios
        for task in tasks_to_run
        for repeat in range(repeats)
    ]
    total = len(all_tuples)

    planned = [
        (sc, task, repeat)
        for sc, task, repeat in all_tuples
        if (bank.name, bank.dataset_version, task.id, sc.config_hash, repeat) not in done
    ]
    already_done = total - len(planned)

    if limit is not None:
        planned = planned[:limit]

    num_planned = len(planned)
    # Per TRIAL, not a flat rate: a series trial spends many spawns, and a
    # single-spawn trial is bounded by the cap actually in force. Both corrections
    # live in `_trial_ceiling_usd`.
    ceiling_usd = sum(_trial_ceiling_usd(sc, task, max_budget_usd) for sc, task, _ in planned)

    # --- Print plan + ceiling BEFORE any spawn (spec §10 invariant) ---
    print(
        f"fathom run: bank={bank.name}  scenarios={len(resolved_scenarios)}"
        f"  tasks={len(tasks_to_run)}  repeats={repeats}",
        file=_out,
    )
    # Name the arms. A wrong --scenarios-dir that happens to hold the same NUMBER of
    # arms prints an identical count line, so the counts alone cannot tell a matrix
    # from the wrong experiment — and the arm names are otherwise only visible after
    # the spend, in the ledger.
    print(f"arms:     {', '.join(sc.name for sc in resolved_scenarios)}", file=_out)
    print(
        f"planned:  {num_planned} trials ({already_done} already done)"
        f"  ceiling: ${ceiling_usd:.2f}",
        file=_out,
    )
    # Show the arithmetic for any multi-spawn arm. A ceiling many times the per-trial
    # rail reads as a typo unless the spawn count is named; naming it is what makes
    # the number actionable (chunk it with --limit, lower the rail, or don't run).
    series_cells: dict[tuple[str, str], list[Any]] = {}
    for sc, task, _ in planned:
        if sc.strategy == "series":
            series_cells.setdefault((sc.name, task.id), [sc, task, 0])[2] += 1
    for (arm, task_id), (sc, task, count) in sorted(series_cells.items()):
        spawn_plan = _series_spawn_plan(task)
        shape = (
            f"{spawn_plan[0]} PRs x (1 impl + {spawn_plan[1]} fix) spawns"
            if spawn_plan is not None
            else "spawn count UNKNOWN (series template unreadable)"
        )
        print(
            f"  series arm {arm}/{task_id}: {count} x "
            f"${_trial_ceiling_usd(sc, task, max_budget_usd):.2f}/trial"
            f"  ({shape}; the per-spawn rail applies to each)",
            file=_out,
        )

    if dry_run:
        print("[dry-run] no spawns", file=_out)
        return EXIT_OK

    if num_planned == 0:
        print("nothing to do", file=_out)
        return EXIT_OK

    # --- Bank validity gate: can this bank measure anything at all? ---------
    # Free (local verifier runs, no spawns) and ordered first, because a bank that
    # cannot discriminate makes the arming question moot: every arm scores 100%
    # and the run returns a null manufactured by the instrument (FATH-B02).
    if skip_bank_validation:
        print("WARNING: --skip-bank-validation: spending on an unvalidated bank", file=_out)
    else:
        import fathom.validate as _validate

        print(f"validate: checking bank '{bank.name}' can discriminate...", file=_out)
        bank_checks = _validate.validate_bank(bank, stage_fn=_stage_fn, verifier_fn=_verifier)
        if not _validate.validation_ok(bank_checks):
            print(_validate.render_validation(bank.name, bank_checks), file=_out)
            print(
                "\nREFUSING TO RUN: this bank cannot measure what it claims to measure.\n"
                "Fix the bank, or re-run with --skip-bank-validation to spend anyway.",
                file=_out,
            )
            return EXIT_BANK_INVALID
        unver = sum(1 for c in bank_checks if c.status == _validate.STATUS_UNVERIFIABLE)
        print(
            f"validate: bank discriminates on all {len(bank.tasks)} task(s)"
            + (f" ({unver} propert(y/ies) unverifiable — see `fathom validate`)" if unver else ""),
            file=_out,
        )

    # --- Arming gate: prove the treatment reached the spawn BEFORE spending ---
    # fathom used to validate declarations only, so an entirely unarmed arm could
    # score 100% over 9 trials with a clean smoke and zero infra errors. A null
    # result from an unarmed arm is indistinguishable from "the tool does not
    # help" — and a null is what the decisions downstream of this harness are
    # looking for, so the instrument's failure mode and the reader's expectation
    # point the same way. Hence: refuse, loudly, rather than warn (FATH-B01).
    if skip_arming_check:
        armed_arms = [sc.name for sc in resolved_scenarios if _arming.needs_verification(sc)]
        if armed_arms:
            print(
                f"WARNING: --skip-arming-check: spending on treatment arms {armed_arms} "
                "WITHOUT proof they are armed",
                file=_out,
            )
    else:
        to_verify = [sc for sc in resolved_scenarios if _arming.needs_verification(sc)]
        probe = arming_probe
        if probe is None and to_verify:
            # Constructed only when there is something to prove, so a matrix of
            # plain control arms neither spawns nor imports the probe.
            from fathom.armingprobe import RealArmingProbe

            probe = RealArmingProbe()
        if to_verify:
            print(
                f"arming: verifying {len(to_verify)} treatment arm(s) on real spawns...",
                file=_out,
            )
        armed_ok, arming_report = _arming.verify_all(resolved_scenarios, probe)
        if arming_report:
            print(arming_report, file=_out)
        if not armed_ok:
            print(
                "\nREFUSING TO RUN: at least one treatment arm could not be proven armed.\n"
                "An unarmed arm scores as the control and manufactures a null result.\n"
                "Fix the arm, or re-run with --skip-arming-check to spend anyway.",
                file=_out,
            )
            return EXIT_UNARMED
        if to_verify:
            print("arming: all declared treatments verified\n", file=_out)

    if executor_factory is not None:
        _executor_factory = executor_factory
    else:

        def _executor_factory(sc: ResolvedScenario) -> Any:
            return _default_executor_factory(sc, max_budget_usd=max_budget_usd)

    if runner_factory is not None:
        _runner_factory = runner_factory
    else:

        def _runner_factory(sc: ResolvedScenario) -> Any:
            return _default_runner_factory(sc, max_budget_usd=max_budget_usd)

    # Spend this INVOCATION has observed. Deliberately not read back from the ledger:
    # `fathom run` is resumable, so `<bank>.jsonl` holds every prior invocation's spend and
    # a ledger-sourced rail would trip at $0 of new spend on the second call — the same
    # shape as the per-spawn cap that read like a program rail and was not one.
    spent_usd = 0.0

    # --- Fixture integrity: the baseline every trial stages from must not move ---
    # An agent that reaches the task directory can edit fixtures/ (it happened: two
    # trials of one matrix wrote a solution and a test file into the fixture, and
    # fourteen later trials staged from it). The manifest is taken once, before any
    # spawn; every trial is checked before it stages and after it returns; drift stops
    # the matrix as an infrastructure failure and never buys a trial against it.
    fixture_expected = {task.id: fixture_manifest(task) for task in tasks_to_run}
    fixture_shas = {task.id: fixture_fingerprint(task) for task in tasks_to_run}

    # --- Execute trials (all spawns happen below this line) ---
    for sc, task, repeat in planned:
        drifted = fixture_drift(task, fixture_expected[task.id])
        if drifted:
            print(
                f"infrastructure error: fixture drift for task {task.id!r} before staging "
                f"({len(drifted)} path(s): {', '.join(drifted[:6])}) — the baseline is not the "
                "committed one; restore fixtures/ and re-run — stopping matrix",
                file=_out,
            )
            return EXIT_INFRASTRUCTURE
        if max_run_usd is not None and spent_usd >= max_run_usd:
            print(
                f"run budget reached: ${spent_usd:.2f} of ${max_run_usd:.2f} spent this "
                "invocation — halting before the next trial. Nothing already bought is "
                "lost; re-invoke to continue from the ledger.",
                file=_out,
            )
            return EXIT_RUN_BUDGET
        # Names the raw-stream file the adapter tees when FATHOM_STREAM_DIR is
        # set (opt-in post-hoc analysis); harmless otherwise.
        os.environ["FATHOM_STREAM_TAG"] = f"{bank.name}--{sc.name}--{task.id}--r{repeat}"
        executor = _executor_factory(sc)
        runner = _runner_factory(sc)

        with _stage_fn(task, _DEFAULT_BASE_BRANCH) as workspace:
            trial_result = executor.run_trial(task, workspace, sc, runner)

            if trial_result.is_infrastructure:
                # The ledger is skipped here on purpose (it is the resume checkpoint), but
                # the spawn was still paid for — so the tally must see it, or the rail
                # silently undercounts exactly on the path that halts a matrix.
                spent_usd += sum(r.cost_usd_est for r in trial_result.runs)
                detail = trial_result.detail or "infrastructure error (auth or usage limit)"
                print(
                    f"infrastructure error: {detail} — stopping matrix",
                    file=_out,
                )
                # Ledger is the resume checkpoint — no writes for this trial.
                return EXIT_INFRASTRUCTURE

            # A trial that reached into the task directory corrupted the baseline for
            # every trial after it; its own result is not scored, and the matrix stops.
            drifted_during = fixture_drift(task, fixture_expected[task.id])

            # Grade the trial while workspace is still live (§7)
            verifier_data: dict[str, Any] | None = None
            verifier_errored = False
            verifier_note = ""
            if drifted_during:
                verifier_errored = True
                verifier_note = (
                    f"fixture drift during trial ({len(drifted_during)} path(s): "
                    f"{', '.join(drifted_during[:6])})"
                )
            # FATH-B14: the verifier's own output is in hand here and used to be
            # dropped, so a failing criterion could not be diagnosed without
            # re-running the trial — and a crashed verifier took its error message
            # with it. Bounded because the ledger is committed: one bad trial must
            # not put a megabyte of agent output into git history.
            verifier_stdout = ""
            verifier_stderr = ""
            if trial_result.scored and not drifted_during:
                verify_entry = task.task_dir / task.verify["entry"]
                verify_timeout = int(task.verify.get("timeout_s", 60))
                vr = _verifier(verify_entry, workspace, timeout_s=verify_timeout)
                verifier_stdout = (vr.stdout or "")[:_VERIFIER_OUTPUT_CAP]
                verifier_stderr = (vr.stderr or "")[:_VERIFIER_OUTPUT_CAP]
                if vr.outcome == "error":
                    # A verifier crash / timeout / non-JSON is NOT a task failure — it
                    # means we have no valid score. Recording it as a completed trial
                    # with verifier_results=None makes the report score it as a silent
                    # FAIL and permanently occupy the resume key. Mark it errored so it
                    # surfaces in the error column and is re-run on resume (spec §6).
                    verifier_errored = True
                    verifier_note = (
                        "verifier error: "
                        + ((vr.stderr or vr.stdout or "non-JSON/crash").strip()[:200])
                    )
                else:
                    verifier_data = vr.criteria

            # Append run records to ledger
            for run_rec in trial_result.runs:
                from fathom.adapters.base import ExitStatus

                spent_usd += run_rec.cost_usd_est
                ledger_run = _ledger.RunRecord(
                    bank=bank.name,
                    task_id=task.id,
                    repeat=repeat,
                    usage=run_rec.usage,
                    turns=run_rec.num_turns,
                    duration=run_rec.duration_s,
                    exit_code=0 if run_rec.status is ExitStatus.OK else 1,
                    dataset_version=bank.dataset_version,
                    config_hash=sc.config_hash,
                    tool_git_sha=sc.tool_repo_sha or "",
                    cli_version=run_rec.cli_version,
                    pin_level=trial_result.pin_level,
                    cost_usd_est=run_rec.cost_usd_est,
                    model_id=run_rec.model_id,
                    config_preimage=sc.config_preimage,
                )
                _ledger.append_record(bank.name, ledger_run, ledger_dir=_ledger_dir)

            # Append trial record (with scenario + holdout for the report renderer).
            # A verifier error downgrades an otherwise-completed trial to errored so it
            # is never scored as a silent FAIL and is re-run on resume (spec §6).
            status_value = "errored" if verifier_errored else trial_result.status.value
            detail = "; ".join(p for p in (trial_result.detail, verifier_note) if p)

            # FATH-B03: a trial that did not run must not look like one that ran and
            # failed. `verifier_results` used to be written for every status except
            # INFRASTRUCTURE, so 166 usage-limit casualties landed as errored trials
            # carrying {correctness: false, footprint: false, trigger_reached: false}
            # — structurally identical to real negatives. The first analysis pass read
            # them as such and depressed every affected arm's rate on a paid analysis
            # until it was caught by hand. Drop the criteria and mark the row invalid,
            # so the distinction is a property of the data rather than a discipline
            # every reader has to remember. Additive and append-only-safe: no existing
            # line is rewritten, and a legacy row without `valid` still loads.
            valid = status_value == "completed"
            if not valid:
                verifier_data = None
            trial_rec = _ledger.TrialRecord(
                bank=bank.name,
                task_id=task.id,
                repeat=repeat,
                status=status_value,
                dataset_version=bank.dataset_version,
                config_hash=sc.config_hash,
                tool_git_sha=sc.tool_repo_sha or "",
                cli_version=trial_result.runs[-1].cli_version if trial_result.runs else "",
                pin_level=trial_result.pin_level,
                verifier_results=verifier_data,
                detail=detail,
                config_preimage=sc.config_preimage,
            )
            trial_dict = dataclasses.asdict(trial_rec)
            trial_dict["valid"] = valid
            trial_dict["verifier_stdout"] = verifier_stdout
            trial_dict["verifier_stderr"] = verifier_stderr
            trial_dict["scenario"] = sc.name
            trial_dict["holdout"] = task.id in bank.holdout
            trial_dict["fixture_sha"] = fixture_shas[task.id]
            _ledger.append_record(bank.name, trial_dict, ledger_dir=_ledger_dir)

            if drifted_during:
                print(
                    f"infrastructure error: fixture drift during trial {sc.name}/{task.id} "
                    f"repeat={repeat} ({', '.join(drifted_during[:6])}) — recorded as errored; "
                    "restore fixtures/ and re-run — stopping matrix",
                    file=_out,
                )
                return EXIT_INFRASTRUCTURE

    return EXIT_OK


def _default_executor_factory(
    scenario: ResolvedScenario, max_budget_usd: float | None = None
) -> Any:
    if scenario.strategy == "series":
        from fathom.strategies.series import SeriesExecutor

        if max_budget_usd is None:
            return SeriesExecutor()
        # `--max-budget-usd` is the per-spawn cost rail, and the engine's spawns are
        # spawns. Without this the flag silently did nothing on a series arm — the
        # runner it caps is the one the engine never uses (ADR-0001) — so the only
        # ceiling in force was SeriesExecutor's own $20/$5/$3 default, and an operator
        # who set the rail believed in one that was not there. Every role gets the
        # same cap because the flag names a per-spawn cap, not a per-role policy.
        return SeriesExecutor(
            budget_impl=max_budget_usd,
            budget_review=max_budget_usd,
            budget_fix=max_budget_usd,
        )
    if scenario.strategy in ("gated-session", "gated-review"):
        from fathom.strategies.gated_session import GatedSessionExecutor

        return GatedSessionExecutor(
            with_review=scenario.strategy == "gated-review",
            extra_gate_cmds=scenario.gate.extra,
        )
    if scenario.strategy == "reprompt-session":
        from fathom.strategies.reprompt_session import RepromptSessionExecutor

        return RepromptSessionExecutor()
    if scenario.strategy == "single-session":
        from fathom.strategies.single_session import SingleSessionExecutor

        return SingleSessionExecutor()
    # Reject anything else LOUDLY. A silent fall-through to single-session would run
    # a typo'd arm (e.g. "gated-sesion") as the bare single-spawn strategy under the
    # intended arm's name — scoring the wrong experiment while looking correct. That
    # is the "unarmed arm" failure class the empty-allowlist / missing-inject / empty-
    # mount warnings already guard; the strategy field gets the same treatment.
    from fathom.strategies import KNOWN_STRATEGIES

    raise ValueError(
        f"unknown strategy {scenario.strategy!r} in scenario {scenario.name!r}; "
        f"known strategies: {', '.join(sorted(KNOWN_STRATEGIES))}"
    )


def _default_runner_factory(scenario: ResolvedScenario, max_budget_usd: float | None = None) -> Any:
    from fathom.adapters.claude_cli import ClaudeCliRunner

    inject = scenario.context.inject
    if scenario.strategy != "series" and not scenario.tools.allowed:
        # Under headless default-deny an empty allowlist leaves the agent with
        # no tools at all — the arm is unarmed, not evaluated.
        print(
            f"WARNING: scenario '{scenario.name}' has an empty tools.allowed list; "
            "under default-deny the agent cannot read or write the workspace",
            file=sys.stderr,
        )
    if inject is not None and not pathlib.Path(inject).is_file():
        # The treatment arm declares an injection file that is missing/unreadable:
        # the spawn would carry no skill body and silently degrade to the control.
        print(
            f"WARNING: scenario '{scenario.name}' declares context.inject but the file is "
            f"missing/unreadable ({inject}); the treatment arm would spawn UN-SKILLED",
            file=sys.stderr,
        )
    settings_file = scenario.settings.inject
    if settings_file is not None and not pathlib.Path(settings_file).is_file():
        # The treatment arm declares a settings.json that is missing/unreadable:
        # the spawn would carry no hook and silently degrade to the control.
        print(
            f"WARNING: scenario '{scenario.name}' declares settings.inject but the file is "
            f"missing/unreadable ({settings_file}); the treatment arm would spawn UN-HOOKED",
            file=sys.stderr,
        )
    for mount_dir in scenario.plugins.mount:
        p = pathlib.Path(mount_dir)
        try:
            is_usable = p.is_dir() and any(p.iterdir())
        except OSError:
            is_usable = False
        if not is_usable:
            # The treatment arm declares a plugin dir that is missing/empty:
            # the spawn would carry no plugin skills and silently degrade to the control.
            print(
                f"WARNING: scenario '{scenario.name}' declares plugins.mount dir "
                f"'{mount_dir}' but it is missing or empty; "
                "the treatment arm would spawn UNARMED (plugin unavailable)",
                file=sys.stderr,
            )
    budget_kw = {} if max_budget_usd is None else {"default_max_budget_usd": max_budget_usd}
    return ClaudeCliRunner(
        allowed_tools=scenario.tools.allowed,
        disallowed_tools=scenario.tools.disallowed,
        append_system_prompt_file=inject,
        plugin_dirs=scenario.plugins.mount,
        settings_file=settings_file,
        **budget_kw,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (called via sys.exit by setuptools)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return _cmd_run(args)
    if args.command == "report":
        return _cmd_report(args)
    if args.command == "void":
        return _cmd_void(args)
    if args.command == "smoke":
        return _cmd_smoke(args)
    if args.command == "verify-arming":
        return _cmd_verify_arming(args)
    if args.command == "reconcile":
        return _cmd_reconcile(args)
    if args.command == "validate":
        return _cmd_validate(args)
    parser.print_help()
    return 1


def _cmd_run(args: argparse.Namespace) -> int:
    from fathom.scenario import load_scenario, resolve_scenario

    tasks_dir: pathlib.Path = args.tasks_dir
    scenarios_dir: pathlib.Path = args.scenarios_dir
    ledger_dir: pathlib.Path = args.ledger_dir or _ledger.LEDGER_DIR

    try:
        bank = load_bank(tasks_dir / args.bank)
    except Exception as exc:
        print(f"error: could not load bank '{args.bank}': {exc}", file=sys.stderr)
        return 1

    resolver = _DefaultResolver()
    resolved_scenarios: list[ResolvedScenario] = []
    for sc_file in sorted(scenarios_dir.glob("*.toml")):
        try:
            config = load_scenario(sc_file)
            resolved = resolve_scenario(config, resolver)
            resolved_scenarios.append(resolved)
        except Exception as exc:
            print(f"warning: skipping scenario {sc_file.name}: {exc}", file=sys.stderr)

    if not resolved_scenarios:
        print(f"error: no scenarios found in {scenarios_dir}", file=sys.stderr)
        return 1

    # Fail fast on an unknown strategy — BEFORE planning or any spawn, so a typo is
    # caught by --dry-run too, not silently run as single-session mid-matrix.
    from fathom.strategies import KNOWN_STRATEGIES

    bad = [sc for sc in resolved_scenarios if sc.strategy not in KNOWN_STRATEGIES]
    if bad:
        for sc in bad:
            print(
                f"error: scenario '{sc.name}' has unknown strategy '{sc.strategy}'; "
                f"known: {', '.join(sorted(KNOWN_STRATEGIES))}",
                file=sys.stderr,
            )
        return 1

    # Two spellings reach the same per-spawn cap. argparse cannot tell which the operator
    # used from one action, and the last-parsed silently winning is exactly the class of
    # quiet money bug this flag already caused once — so they are separate dests and the
    # disagreement is an error rather than a coin toss.
    spawn_cap = args.max_spawn_usd
    if args.legacy_max_budget_usd is not None:
        if spawn_cap is not None and spawn_cap != args.legacy_max_budget_usd:
            print(
                "error: --max-spawn-usd and --max-budget-usd both given with different "
                f"values ({spawn_cap} vs {args.legacy_max_budget_usd}). They are the same "
                "cap; pass one.",
                file=sys.stderr,
            )
            return 1
        if spawn_cap is None:
            print(
                "note: --max-budget-usd is the old spelling of --max-spawn-usd. It still "
                "works and will keep working; the new name says what it caps.",
                file=sys.stderr,
            )
            spawn_cap = args.legacy_max_budget_usd

    return run_matrix(
        bank,
        resolved_scenarios,
        args.repeats,
        dry_run=args.dry_run,
        limit=args.limit,
        task_ids=(
            [t.strip() for t in args.tasks.split(",") if t.strip()]
            if args.tasks is not None
            else None
        ),
        ledger_dir=ledger_dir,
        max_budget_usd=spawn_cap,
        max_run_usd=args.max_run_usd,
        include_holdout=args.include_holdout,
        skip_arming_check=args.skip_arming_check,
        skip_bank_validation=args.skip_bank_validation,
    )


def _load_resolved_scenarios(scenarios_dir: pathlib.Path) -> list[ResolvedScenario]:
    """Parse and resolve every arm in *scenarios_dir*, skipping unparsable files."""
    from fathom.scenario import load_scenario, resolve_scenario

    resolver = _DefaultResolver()
    out: list[ResolvedScenario] = []
    for sc_file in sorted(scenarios_dir.glob("*.toml")):
        try:
            out.append(resolve_scenario(load_scenario(sc_file), resolver))
        except Exception as exc:  # noqa: BLE001 - one bad arm must not hide the rest
            print(f"warning: skipping scenario {sc_file.name}: {exc}", file=sys.stderr)
    return out


def _cmd_validate(args: argparse.Namespace) -> int:
    """Check the bank-validation triad. Free — local verifier runs, no spawns."""
    import fathom.validate as _validate

    try:
        bank = load_bank(args.tasks_dir / args.bank)
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not load bank '{args.bank}': {exc}", file=sys.stderr)
        return 1

    checks = _validate.validate_bank(bank, stage_fn=stage_task, verifier_fn=run_verifier)
    print(_validate.render_validation(bank.name, checks))
    return EXIT_OK if _validate.validation_ok(checks, strict=args.strict) else EXIT_BANK_INVALID


def _cmd_verify_arming(args: argparse.Namespace) -> int:
    """Prove every declaring arm in a scenarios dir is armed, on real spawns."""
    from fathom.armingprobe import RealArmingProbe

    scenarios = _load_resolved_scenarios(args.scenarios_dir)
    if not scenarios:
        print(f"error: no scenarios found in {args.scenarios_dir}", file=sys.stderr)
        return 1

    declaring = [sc for sc in scenarios if _arming.needs_verification(sc)]
    print(
        f"verify-arming: {len(scenarios)} arm(s) in {args.scenarios_dir}, "
        f"{len(declaring)} declaring a treatment axis"
    )
    for sc in scenarios:
        axes = _arming.declared_axes(sc)
        print(f"  {sc.name}: {', '.join(axes) if axes else '(control — nothing to verify)'}")
    if not declaring:
        return EXIT_OK

    print("\nspawning one cheap probe per declaring arm...\n")
    ok, report = _arming.verify_all(scenarios, RealArmingProbe())
    print(report)
    print("\nARMING RESULT:", "ALL VERIFIED" if ok else "SOME ARMS ARE NOT ARMED")
    return EXIT_OK if ok else EXIT_UNARMED


def _warn_if_unpublished(bank: str) -> None:
    """Warn when a bank's conclusion is findable in neither a report nor STATUS.

    Rendering the scorecard is free and repeatable; publishing the verdict where a
    consumer can find it is the step that was unenforced prose and recurred until
    five analyses' conclusions survived only in commit messages — one of which a
    sibling backlog was citing to retire a shipped surface (FATH-B06). The warn
    helps in the moment; `tests/test_ledger_coverage.py` is the part that binds.
    """
    reports_dir = pathlib.Path("docs") / "reports"
    status = pathlib.Path("docs") / "STATUS.md"
    try:
        in_report = any(
            bank in p.name or bank in p.read_text(encoding="utf-8", errors="replace")
            for p in reports_dir.glob("*.md")
        )
        in_status = status.is_file() and bank in status.read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        return
    if not in_report and not in_status:
        print(
            f"WARNING: no docs/reports/ entry and no docs/STATUS.md row mentions "
            f"'{bank}'. The scorecard regenerates for free; the verdict does not. "
            f"Write it up before the conclusion survives only in a commit message.",
            file=sys.stderr,
        )


def void_trial(
    bank: str,
    scenario: str,
    repeat: int,
    reason: str,
    *,
    task_id: str | None = None,
    evidence: str = "",
    ledger_dir: pathlib.Path | None = None,
) -> _ledger.VoidRecord:
    """Append a void row for the latest recorded trial matching (scenario, repeat[, task]).

    Raises ``LookupError`` when no such trial row exists — a void must name a recorded
    trial, never a key that was never bought.
    """
    import datetime as _dt

    _dir = ledger_dir if ledger_dir is not None else _ledger.LEDGER_DIR
    target: dict[str, Any] | None = None
    # Raw rows, not `iter_records`: the dataclass view drops the extra keys the run loop
    # writes (`scenario`, `valid`, ...), and the arm name is exactly what is matched here.
    path = _dir / f"{bank}.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict) or row.get("kind") != "trial":
            continue
        if row.get("scenario") != scenario or int(row.get("repeat", -1)) != repeat:
            continue
        if task_id is not None and row.get("task_id") != task_id:
            continue
        target = row
    if target is None:
        raise LookupError(
            f"no trial row for scenario={scenario!r} repeat={repeat}"
            + (f" task={task_id!r}" if task_id else "")
            + f" in ledger {bank!r}"
        )
    void = _ledger.VoidRecord(
        bank=bank,
        task_id=str(target.get("task_id", "")),
        repeat=repeat,
        dataset_version=str(target.get("dataset_version", "")),
        config_hash=str(target.get("config_hash", "")),
        scenario=scenario,
        reason=reason,
        evidence=evidence,
        voided_at=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    )
    _ledger.append_record(bank, void, ledger_dir=_dir)
    return void


def _cmd_void(args: argparse.Namespace) -> int:
    ledger_dir = pathlib.Path(args.ledger_dir) if args.ledger_dir else None
    try:
        void = void_trial(
            args.bank,
            args.scenario,
            args.repeat,
            args.reason,
            task_id=args.task_id,
            evidence=args.evidence,
            ledger_dir=ledger_dir,
        )
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"voided {void.scenario} repeat={void.repeat} task={void.task_id}: {void.reason}")
    return EXIT_OK


def _cmd_report(args: argparse.Namespace) -> int:
    import fathom.report as _report

    try:
        out_path = _report.render(args.bank)
        print(f"report written to {out_path}")
        _warn_if_unpublished(args.bank)
        return EXIT_OK
    except Exception as exc:
        print(f"error rendering report: {exc}", file=sys.stderr)
        return 1


def _cmd_reconcile(args: argparse.Namespace) -> int:
    """Run the reconciliations; free, spawns nothing.

    Two failure directions, and the second is the one that keeps the gate honest: an
    unexcused discrepancy means two derivations of one fact disagree, and a *stale*
    exception means an excuse outlived the thing it excused.
    """
    from fathom import reconcile as _reconcile

    if getattr(args, "list_checks", False):
        for check in _reconcile.CHECKS:
            print(f"{check.name:<24} {check.describe}")
        return EXIT_OK

    try:
        found = _reconcile.run_all(names=args.checks)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNRECONCILED

    bad = _reconcile.unexpected(found)
    stale = _reconcile.stale_exceptions(found)
    excused = len(found) - len(bad)

    for d in bad:
        print(f"[DISAGREES] {d}")
    for fp in stale:
        print(
            f"[STALE EXCEPTION] {fp} no longer excuses anything — delete it; an "
            "exception that outlives its discrepancy silently widens the gate"
        )

    have, total = _reconcile.preimage_coverage(_reconcile.REPO)
    pct = (100.0 * have / total) if total else 0.0
    print(
        f"preimage coverage: {have}/{total} ledger rows ({pct:.0f}%) carry the second "
        "derivation the exact check needs. Rows written before 0.4.0 carry none; that is a "
        "coverage gap, reported rather than excused, and it only shrinks as trials are bought."
    )
    checks = _reconcile.registry(args.checks)
    print("")
    print(
        f"RECONCILE: {'OK' if not bad and not stale else 'FAILED'} "
        f"({len(checks)} check(s), {len(bad)} disagreement(s), "
        f"{excused} excused, {len(stale)} stale exception(s))"
    )
    return EXIT_OK if not bad and not stale else EXIT_UNRECONCILED


def _cmd_smoke(args: argparse.Namespace) -> int:
    from fathom.smoke import RealProbes, run_smoke

    probes = RealProbes()
    return run_smoke(
        probes,
        force_fail=args.force_fail,
        include_engine=not args.no_engine_boundary,
    )


class _DefaultResolver:
    """Real scenario resolver: git for tool SHA, uv run for invocation command."""

    def resolve_model_id(self, model: str) -> str | None:
        return None  # deferred; CLI reports the exact model id at run time

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

    def resolve_plugin_meta(self, plugin_dir: str) -> tuple[str, str, str]:
        import hashlib
        import json

        plugin_path = pathlib.Path(plugin_dir)
        plugin_json = plugin_path / ".claude-plugin" / "plugin.json"
        with open(plugin_json) as f:
            meta = json.load(f)
        name: str = meta["name"]
        version: str = meta["version"]

        # tree_sha: sha256 over every file's relative path + contents under the
        # plugin dir (sorted for determinism), EXCEPT the _SKIP names below. This
        # globs the filesystem — it does NOT consult git — so an untracked scratch or
        # editor-backup file inside the mounted dir also enters the hash and forks the
        # arm's config_hash/resume key; the skiplist only covers the usual cache/vcs
        # churn, so keep a mounted plugin dir otherwise clean (spec §2 / ADR-0002).
        _SKIP = frozenset({"__pycache__", ".venv", ".git", ".in_use", ".orphaned_at"})
        h = hashlib.sha256()
        for fp in sorted(plugin_path.rglob("*")):
            if fp.is_dir():
                continue
            if _SKIP & set(fp.relative_to(plugin_path).parts):
                continue
            rel = fp.relative_to(plugin_path).as_posix()
            h.update(rel.encode())
            h.update(fp.read_bytes())
        return name, version, h.hexdigest()
