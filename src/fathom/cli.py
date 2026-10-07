"""CLI entry point — ``fathom <command>`` (spec §10).

Every command that reads or writes data runs against one data root, found by
:func:`fathom.home.resolve`: ``--home``, else ``FATHOM_HOME``, else the nearest directory at
or above the working directory whose ``fathom.toml`` has a ``[data_root]`` table, else an
unmarked working directory that holds ``tasks/`` or ``ledger/`` (with a warning). Path
options a user passes (``--tasks-dir``, ``--scenarios-dir``, ``--ledger-dir``) keep their
usual meaning, relative to the working directory the command was started in; every default
path is the data root's own. The command then runs with the data root as its working
directory, like ``git -C``, so it behaves the same from anywhere.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import os
import pathlib
import statistics
import sys
import tomllib
from collections.abc import Callable, Iterator, Sequence
from typing import Any, TextIO

import fathom.arming as _arming
import fathom.home as _home
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
# Relative to the data root, which is the working directory while a command runs.
SCENARIOS_DIR = pathlib.Path("scenarios")
TASKS_DIR = pathlib.Path("tasks")

# Named exit codes (spec §10)
EXIT_OK = 0
EXIT_INFRASTRUCTURE = 10
EXIT_UNARMED = 11  # a treatment arm could not be proven armed (FATH-B01)
EXIT_BANK_INVALID = 12  # the bank cannot discriminate between arms (FATH-B02)
EXIT_UNRECONCILED = 13  # two derivations of one fact disagree (FATH-B62/B63)
EXIT_RUN_BUDGET = 14  # the per-invocation spend rail halted the matrix (FATH-B04)
EXIT_CREDENTIAL = 15  # the seat has too little credential life to start (FATH-B04)
EXIT_STOPPED = 16  # `fathom stop` halted the matrix at a trial boundary (FATH-B53)


def _installed_version() -> str:
    """The version of the installed ``fathom`` distribution, read from its metadata.

    Read rather than copied into the source, so it is always the version a data root
    actually installed. Running from a source tree that was never installed has no
    metadata, and says so.
    """
    from importlib import metadata

    try:
        return metadata.version("fathom")
    except metadata.PackageNotFoundError:
        return "unknown (not installed as a package)"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fathom",
        description="Scenario-blind tool-effectiveness evals",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_installed_version()}",
        help="Print the installed fathom version and exit",
    )
    p.add_argument(
        "--home",
        default=None,
        metavar="DIR",
        help="The data root to run against. Default: $FATHOM_HOME, else the nearest "
        "directory at or above the working directory whose fathom.toml has a [data_root] "
        "table.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser(
        "init",
        help="Create a data root: fathom.toml, tasks/, scenarios/, ledger/, docs/reports/, "
        ".gitignore, .gitattributes (never overwrites a file)",
    )
    init_p.add_argument(
        "dir",
        nargs="?",
        default=None,
        metavar="DIR",
        help="Where to create it (default: --home if given, else the working directory)",
    )

    run_p = sub.add_parser("run", help="Execute the scenario matrix against a task bank")
    run_p.add_argument("bank", help="Bank name (the tasks/<bank>/ directory of the data root)")
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
        default=None,
        dest="scenarios_dir",
        metavar="DIR",
        help="Directory globbed (non-recursively) for arm *.toml (default: the data root's "
        "scenarios/). REQUIRED for a bank that ships its own arms in a subdir, or the wrong "
        "arms run.",
    )
    run_p.add_argument(
        "--tasks-dir",
        type=pathlib.Path,
        default=None,
        dest="tasks_dir",
        metavar="DIR",
        help="Directory holding <bank>/ task banks (default: the data root's tasks/).",
    )
    run_p.add_argument(
        "--ledger-dir",
        type=pathlib.Path,
        default=None,
        dest="ledger_dir",
        metavar="DIR",
        help="Directory for the append-only <bank>.jsonl ledger (default: the data root's "
        "ledger/).",
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
        # timer: it appears in analysis reports (which record what was actually run and
        # must not be rewritten) and inside mounted plugin trees whose bytes are
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
        "n_prs x (1 impl + fixes + reviews) spawns on a series arm). Resuming is safe: the "
        "ledger is the checkpoint, so a halt costs nothing already bought.",
    )

    run_p.add_argument(
        "--skip-bank-validation",
        action="store_true",
        dest="skip_bank_validation",
        help="Spend WITHOUT checking that the bank can discriminate. The check is "
        "free, and a bank that cannot discriminate buys a null result at full price; "
        "skip it only when re-running a bank validated this session.",
    )
    run_p.add_argument(
        "--skip-arming-check",
        action="store_true",
        dest="skip_arming_check",
        help="Spend WITHOUT proving the treatment arms are armed. The arming gate "
        "costs a fraction of a cent per arm, and an unarmed arm scores as the control "
        "while looking like a treatment; skip it only to re-run a matrix whose "
        "arming was already verified this session.",
    )
    run_p.add_argument(
        "--skip-credential-check",
        action="store_true",
        dest="skip_credential_check",
        help="Start WITHOUT checking that the seat has credential life left. The "
        "check is free and reads two timestamps (never a token); it exists because "
        "matrices have repeatedly started, spawned and died on auth. Skip it only "
        "when the credential lives somewhere this check cannot see.",
    )
    run_p.add_argument(
        "--no-lock",
        action="store_true",
        dest="no_lock",
        help="Spend WITHOUT serializing against other runs of this bank. A paid "
        "matrix consumes one seat's credential and rate budget, so two concurrent "
        "runs interfere; the lock is free and self-healing (a holder silent past the "
        "staleness horizon is released). Use only when the concurrent run is on "
        "another seat.",
    )
    run_p.add_argument(
        "--lock-wait-s",
        type=float,
        default=None,
        dest="lock_wait_s",
        metavar="SECONDS",
        help="Give up waiting for the lock after SECONDS (default: wait). Waiting is "
        "the default because a wait that gives up is how two matrices end up on one "
        "seat anyway; a DEAD holder is not a reason to wait, and expires on its own.",
    )

    stop_p = sub.add_parser(
        "stop",
        help="Ask the run holding a bank's lock to stop at its next trial boundary",
    )
    stop_p.add_argument("bank", help="Bank name, as passed to `fathom run`")
    stop_p.add_argument(
        "--at-boundary",
        action="store_true",
        dest="at_boundary",
        help="The default, spelled out: halt after the trial in flight finishes. The "
        "ledger is the resume checkpoint, so nothing already bought is lost.",
    )
    stop_p.add_argument(
        "--now",
        action="store_true",
        dest="now",
        help="Also terminate the holder's process tree. Use when a run is wedged "
        "INSIDE a spawn and will not reach a boundary — it discards the in-flight "
        "trial's spend, which is the cost of not waiting.",
    )
    stop_p.add_argument(
        "--reason",
        default="",
        help="Recorded with the request and printed by the run that honours it",
    )
    stop_p.add_argument("--lock-root", default=None, help=argparse.SUPPRESS)

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
    void_p.add_argument(
        "--ledger-dir",
        type=pathlib.Path,
        default=None,
        dest="ledger_dir",
        metavar="DIR",
        help="Directory holding <bank>.jsonl (default: the data root's ledger/).",
    )

    report_p = sub.add_parser("report", help="Render a scorecard from the ledger")
    report_p.add_argument("bank", help="Bank name")

    val_p = sub.add_parser(
        "validate",
        help="Check the bank-validation triad before any spend (free — no spawns)",
    )
    val_p.add_argument("bank", help="Bank name (the tasks/<bank>/ directory of the data root)")
    val_p.add_argument(
        "--tasks-dir",
        type=pathlib.Path,
        default=None,
        dest="tasks_dir",
        metavar="DIR",
        help="Directory holding <bank>/ task banks (default: the data root's tasks/).",
    )
    val_p.add_argument(
        "--scenarios-dir",
        type=pathlib.Path,
        default=None,
        dest="scenarios_dir",
        metavar="DIR",
        help="Directory globbed for arm *.toml, read only to note where `fathom run` will "
        "keep the agent streams of arms with an injected context or a non-default tool "
        "allowance (default: the data root's scenarios/).",
    )
    val_p.add_argument(
        "--strict",
        action="store_true",
        help="Also fail on UNVERIFIABLE properties (no reference solution, no gate).",
    )

    arm_p = sub.add_parser(
        "verify-arming",
        help="Prove, on a real spawn, that each treatment arm is actually armed (spends a little)",
    )
    arm_p.add_argument(
        "--scenarios-dir",
        type=pathlib.Path,
        default=None,
        dest="scenarios_dir",
        metavar="DIR",
        help="Directory globbed (non-recursively) for arm *.toml (default: the data root's "
        "scenarios/).",
    )

    rec_p = sub.add_parser(
        "reconcile",
        help=(
            "Check every fact the data root derives twice (free — no spawns); in an "
            "engine checkout, its version sites"
        ),
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
    index_p = sub.add_parser(
        "index",
        help="Check the data root's ledger index (docs/reports/LEDGER-INDEX.md) against its "
        "ledgers, or re-render it with --write (free — no spawns)",
    )
    index_p.add_argument(
        "--write",
        action="store_true",
        help="Re-render the index; commit it with the ledgers it stamps",
    )

    smoke_p = sub.add_parser(
        "smoke",
        help="Check spawn isolation on real spawns; run it before any paid matrix "
        "(spends a little)",
    )
    smoke_p.add_argument(
        "--force-fail",
        action="store_true",
        help="Append a forced failing check to demonstrate the nonzero exit path",
    )
    smoke_p.add_argument(
        "--no-engine-boundary",
        action="store_true",
        help="Skip the engine-boundary check, which reads the data root's series arm",
    )

    return p


@dataclasses.dataclass(frozen=True)
class _SeriesSpawnPlan:
    """The most spawns one series trial can make, per PR, by role."""

    n_prs: int
    fixes: int  # fix spawns per PR: the template's max_fix_attempts
    reviews: int  # review spawns per PR: 0 without a blocking review gate

    def describe(self) -> str:
        roles = f"1 impl + {self.fixes} fix"
        if self.reviews:
            roles += f" + {self.reviews} review"
        return f"{self.n_prs} PRs x ({roles}) spawns"


def _series_spawn_plan(task: Task) -> _SeriesSpawnPlan | None:
    """The spawn counts a task's committed series template allows.

    Each PR gets one implementation spawn and up to ``max_fix_attempts`` fix spawns.
    When ``[review] blocking`` is true, the engine also reviews the PR, and reviews
    again after each fix, so up to ``1 + max_fix_attempts`` review spawns; a
    non-blocking or absent review adds none.

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
    blocking = False
    if isinstance(review, dict):
        if isinstance(review.get("max_fix_attempts"), int):
            attempts = review["max_fix_attempts"]
        blocking = review.get("blocking") is True
    fixes = max(0, attempts)
    return _SeriesSpawnPlan(n_prs=len(prs), fixes=fixes, reviews=1 + fixes if blocking else 0)


def _trial_ceiling_usd(
    scenario: ResolvedScenario, task: Task, max_budget_usd: float | None
) -> float:
    """Worst-case USD for ONE trial of `scenario` on `task`.

    Two corrections to a flat per-trial rate, both of which made the plan understate
    what a run could spend, and neither of which the other catches.

    **Spawns per trial.** One spawn per trial is true of every single-spawn strategy
    and false of `series`, which spends one implementation spawn plus up to
    `max_fix_attempts` fix spawns for EVERY PR in the task's decomposition, and, when
    the template's review gate is blocking, up to `1 + max_fix_attempts` review spawns
    per PR as well, each against its own per-spawn cap (:func:`_series_spawn_plan`).
    Pricing that at one spawn is not a conservative estimate — it is a bound the
    operator believes and the run exceeds by an order of magnitude, which is exactly
    what the upfront ceiling exists to prevent (spec §10 / C4).

    **The cap actually in force.** `--max-budget-usd` is PER-SPAWN, so passing a
    number larger than the adapter's default LOOSENS the only runaway guard there is.
    With a hardcoded single-spawn price, the plan printed the same reassuring total
    either way, and a large loosening read as a tight total rail. Deriving it from the
    cap makes the flag's real effect visible in the plan, before the spend.
    """
    per_spawn = max_budget_usd if max_budget_usd is not None else _DEFAULT_SPAWN_BUDGET_USD
    if scenario.strategy != "series":
        return per_spawn
    plan = _series_spawn_plan(task)
    if plan is None:
        return per_spawn
    from fathom.strategies.series import (
        DEFAULT_BUDGET_FIX,
        DEFAULT_BUDGET_IMPL,
        DEFAULT_BUDGET_REVIEW,
    )

    # The same per-role budgets `_default_executor_factory` hands SeriesExecutor: the
    # cap for every role when one is given, else the executor's own defaults.
    impl = max_budget_usd if max_budget_usd is not None else DEFAULT_BUDGET_IMPL
    fix = max_budget_usd if max_budget_usd is not None else DEFAULT_BUDGET_FIX
    review = max_budget_usd if max_budget_usd is not None else DEFAULT_BUDGET_REVIEW
    return plan.n_prs * (impl + plan.fixes * fix + plan.reviews * review)


# A (strategy, model) group needs this many completed trials before the plan quotes its own
# median; a thinner group would put one lucky trial in front of the operator as a typical one.
_MIN_MODEL_ROWS = 5


@dataclasses.dataclass(frozen=True)
class _TrialCost:
    """What one completed trial in the ledger cost: the sum of its run rows' ``cost_usd_est``."""

    strategy: str
    model: str
    usd: float


def _history_trial_costs(
    bank_name: str,
    ledger_dir: pathlib.Path,
    scenarios: Sequence[ResolvedScenario] = (),
) -> list[_TrialCost]:
    """Per-trial cost of every completed trial in the bank's ledger, voids applied.

    Read-only. A trial's cost is the sum of ``cost_usd_est`` over its run rows, which are
    written before the trial row that closes them; a retried key therefore costs what its
    completed attempt cost, not what an errored attempt before it spent. A trial is left
    out, never counted as free, when it has no run rows or any run row says
    ``cost_source == "none"`` (FATH-B79: a missing cost is a gap). Strategy and model come
    from the trial row's ``config_preimage``, or from the one of ``scenarios`` with the
    same ``config_hash`` when the row has none; a trial that names neither is left out.
    """
    from fathom import ledgerindex

    path = ledger_dir / f"{bank_name}.jsonl"
    if not path.exists():
        return []
    by_hash = {sc.config_hash: sc for sc in scenarios}
    pending: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    out: list[_TrialCost] = []
    for row in _ledger.apply_voids(ledgerindex.rows(path)):
        kind = row.get("kind")
        if kind not in ("run", "trial"):
            continue
        key = (
            row.get("dataset_version"),
            row.get("config_hash"),
            row.get("task_id"),
            row.get("repeat"),
        )
        if kind == "run":
            pending.setdefault(key, []).append(row)
            continue
        runs = pending.pop(key, [])
        if row.get("status") != "completed" or not runs:
            continue
        if any(r.get("cost_source", "reported") == "none" for r in runs):
            continue
        strategy = model = None
        try:
            preimage = json.loads(row.get("config_preimage") or "{}")
        except ValueError:
            preimage = {}
        if isinstance(preimage, dict):
            strategy, model = preimage.get("strategy"), preimage.get("model")
        if not (strategy and model) and row.get("config_hash") in by_hash:
            sc = by_hash[row["config_hash"]]
            strategy, model = sc.strategy, sc.model
        if not (strategy and model):
            continue
        try:
            usd = sum(float(r.get("cost_usd_est") or 0.0) for r in runs)
        except (TypeError, ValueError):
            continue
        out.append(_TrialCost(str(strategy), str(model), usd))
    return out


def _expected_spend_line(
    planned: Sequence[tuple[ResolvedScenario, Task, int]],
    history: Sequence[_TrialCost],
) -> str | None:
    """The plan's one-line estimate of what ``planned`` will cost, or None to print nothing.

    Beside the ceiling, not instead of it: the ceiling is what the caps allow, this is what
    trials like these have cost in the same ledger. It is an estimate and gates nothing.
    A planned trial is priced at the median of its (strategy, model) group when that group
    holds at least ``_MIN_MODEL_ROWS`` trials, else at its strategy's median; a planned
    strategy with no history is named and left out of the sum.
    """
    if not planned or not history:
        return None
    by_strategy: dict[str, list[float]] = {}
    by_model: dict[tuple[str, str], list[float]] = {}
    for h in history:
        by_strategy.setdefault(h.strategy, []).append(h.usd)
        by_model.setdefault((h.strategy, h.model), []).append(h.usd)
    median_of_strategy = {k: statistics.median(v) for k, v in by_strategy.items()}
    median_of_model = {
        k: statistics.median(v) for k, v in by_model.items() if len(v) >= _MIN_MODEL_ROWS
    }

    total = 0.0
    priced = 0
    unpriced: dict[str, int] = {}
    used_strategies: set[str] = set()
    used_models: set[tuple[str, str]] = set()
    for sc, _task, _repeat in planned:
        model_key = (sc.strategy, sc.model)
        if model_key in median_of_model:
            total += median_of_model[model_key]
            used_models.add(model_key)
        elif sc.strategy in median_of_strategy:
            total += median_of_strategy[sc.strategy]
        else:
            unpriced[sc.strategy] = unpriced.get(sc.strategy, 0) + 1
            continue
        priced += 1
        used_strategies.add(sc.strategy)

    parts = [
        f"{name} ${med:.2f} n={len(by_strategy[name])}"
        for name, med in sorted(median_of_strategy.items())
        if name in used_strategies
    ] + [
        f"{s}/{m} ${median_of_model[(s, m)]:.2f} n={len(by_model[(s, m)])}"
        for s, m in sorted(used_models)
    ]
    gaps = "; ".join(
        f"no history for strategy {name} ({count} planned trials)"
        for name, count in sorted(unpriced.items())
    )
    if not priced:
        return f"expected: not estimated; {gaps}; an estimate, not a cap"
    line = (
        f"expected: ~${total:.2f} for {priced} planned trials (median per trial from "
        f"{len(history)} completed trials in this ledger: {'; '.join(parts)}"
    )
    if gaps:
        line += f"; {gaps}"
    return line + "); an estimate, not a cap"


# Where a treatment arm's agent streams are kept by default. An arm with a [context]
# inject or a non-default tool allowance keeps its stream, because the stream is the
# only record of what its agent actually did: there is no ledger-side invocation
# counter, and a stream that was opt-in and not kept cannot be recovered after the
# fact. Not under ledger/: that directory is tracked, so a stream file there becomes a
# committed artifact the first time anyone runs `git add ledger/` (same reasoning as
# runlock's LOCK_ROOT). Relative to the data root, the working directory while a
# command runs.
_STREAM_ROOT = pathlib.Path(".fathom") / "streams"


def _wants_stream_dir(sc: ResolvedScenario) -> bool:
    """True for the arms this row is about: a ``[context]`` inject, or tools
    beyond the unarmed default.

    "default" tools is the same distinction ``scenario._tools_to_dict`` already
    encodes for hashing: ``source == "none"`` with no explicit ``allowed`` or
    ``disallowed`` list is the one config with no declared tool access at all.
    Anything else — an explicit allowlist (every armed single-session arm has
    one; an empty one is unarmed, not evaluated) or ``source == "repo"`` — is a
    declared grant, and the treatment being measured needs its stream kept.
    """
    if sc.context.inject:
        return True
    tools = sc.tools
    return tools.source != "none" or bool(tools.allowed) or bool(tools.disallowed)


def _default_stream_dir(bank_name: str) -> pathlib.Path:
    """Where an armed arm's streams are kept: ``.fathom/streams/<bank>`` under the data
    root, made absolute so the path in FATHOM_STREAM_DIR means the same to any reader."""
    return pathlib.Path.cwd() / _STREAM_ROOT / bank_name


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
    run_lock: Any | None = None,
    out: TextIO | None = None,
) -> int:
    """Execute or plan a scenario matrix against a task bank.

    Prints the upfront trial/spawn counts and cost ceiling BEFORE any spawn
    (spec §10).  Returns EXIT_OK (0) or EXIT_INFRASTRUCTURE (10).

    An infrastructure error from any executor (auth / usage-limit) stops the
    matrix cleanly: the affected trial is not scored, the ledger is untouched
    as the resume checkpoint, and EXIT_INFRASTRUCTURE is returned.

    ``run_lock`` is an acquired :class:`fathom.runlock.RunLock`.  When one is given,
    every trial boundary is also a stop point: a request placed by ``fathom stop``
    halts the matrix with ``EXIT_STOPPED`` before the next trial starts, so no caller
    needs a watcher script of its own.  Passing ``None`` (the default, and what every
    test does) changes nothing.
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
    print(
        f"arms:     {', '.join(f'{sc.name} [{sc.config_hash[:12]}]' for sc in resolved_scenarios)}",
        file=_out,
    )
    print(
        f"planned:  {num_planned} trials ({already_done} already done)"
        f"  ceiling: ${ceiling_usd:.2f}",
        file=_out,
    )
    # What trials like these have cost in this ledger, beside the worst-case ceiling above.
    # Information only: the money rail stays on observed spend, and a printed estimate
    # changes no exit code. After the `planned:` line, never inside it, which the
    # acceptance harness matches whole. Nothing is printed without history.
    expected = _expected_spend_line(
        planned, _history_trial_costs(bank.name, _ledger_dir, resolved_scenarios)
    )
    if expected:
        print(expected, file=_out)
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
            spawn_plan.describe()
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
    # Validating declarations alone lets an entirely unarmed arm score like the control
    # across a whole matrix, with a clean smoke and zero infra errors. A null
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
    # An agent that reaches the task directory can edit fixtures/, writing a solution
    # or a test into the baseline that every later trial then stages from. The
    # manifest is taken once, before any
    # spawn; every trial is checked before it stages and after it returns; drift stops
    # the matrix as an infrastructure failure and never buys a trial against it.
    fixture_expected = {task.id: fixture_manifest(task) for task in tasks_to_run}
    fixture_shas = {task.id: fixture_fingerprint(task) for task in tasks_to_run}

    # An explicit FATHOM_STREAM_DIR always wins. Captured once, before any
    # trial, so it is not lost if an earlier trial in this same matrix needed no
    # default and cleared the env var (see the per-trial branch below).
    _explicit_stream_dir = os.environ.get("FATHOM_STREAM_DIR")

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
        # The trial boundary is the stop point, for the same reason the budget rail
        # halts here: the ledger is the checkpoint, so halting between trials loses
        # nothing already bought, while killing a tree mid-trial discards a spawn that
        # has already been paid for.
        if run_lock is not None:
            stop = run_lock.stop_requested()
            if stop is not None:
                run_lock.clear_stop_request()
                because = f" ({stop.reason})" if stop.reason else ""
                print(
                    f"stop requested{because} — halting before the next trial. Nothing "
                    "already bought is lost; re-invoke to continue from the ledger.",
                    file=_out,
                )
                return EXIT_STOPPED
        # Default FATHOM_STREAM_DIR, per trial, for an arm whose scenario
        # declares a [context] inject or a non-default tool allowance — the
        # kind of arm where the stream is the only record of what the agent
        # actually did. An explicit value (set before this invocation) always
        # wins; a bare control arm gets none, even mid-matrix after an armed
        # arm defaulted one for an earlier trial.
        if _explicit_stream_dir:
            os.environ["FATHOM_STREAM_DIR"] = _explicit_stream_dir
        elif _wants_stream_dir(sc):
            os.environ["FATHOM_STREAM_DIR"] = str(_default_stream_dir(bank.name))
        else:
            os.environ.pop("FATHOM_STREAM_DIR", None)
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
                    scenario=sc.name,
                    cost_usd_est=run_rec.cost_usd_est,
                    cost_source=run_rec.cost_source,
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
            # failed. When `verifier_results` was written for every status except
            # INFRASTRUCTURE, usage-limit casualties landed as errored trials carrying
            # all-false criteria — structurally identical to real negatives — and an
            # analysis that read them as such depressed every affected arm's rate.
            # Drop the criteria and mark the row invalid,
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
        # The declared files lie under the data root, and a path in the argv reaches the
        # agent: each spawn gets copies of its own (ADR-0003).
        stage_files=True,
        settings_file=settings_file,
        **budget_kw,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (called via sys.exit by setuptools)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # These find their own root, or need none: `init` creates one, `reconcile` and
    # `index` also accept an engine checkout, and `smoke` needs a data root only for its
    # engine-boundary check.
    if args.command == "init":
        return _cmd_init(args)
    if args.command == "reconcile":
        return _cmd_reconcile(args)
    if args.command == "index":
        return _cmd_index(args)
    if args.command == "smoke":
        return _cmd_smoke(args)

    handlers: dict[str, Callable[[argparse.Namespace], int]] = {
        "run": _cmd_run,
        "report": _cmd_report,
        "void": _cmd_void,
        "stop": _cmd_stop,
        "verify-arming": _cmd_verify_arming,
        "validate": _cmd_validate,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    try:
        root = _home.resolve(args.home)
    except _home.DataRootError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    with _running_in(root, args):
        return handler(args)


# Path options, and the data root's own path each takes when it is not given.
_PATH_DEFAULTS: dict[str, pathlib.Path] = {
    "tasks_dir": TASKS_DIR,
    "scenarios_dir": SCENARIOS_DIR,
    "ledger_dir": _ledger.LEDGER_DIR,
}


def _absolute(base: pathlib.Path, value: str | os.PathLike[str]) -> pathlib.Path:
    """*value* made absolute against *base*, the way a shell user means a relative path."""
    return pathlib.Path(os.path.abspath(base / pathlib.Path(value).expanduser()))


def _anchor_paths(args: argparse.Namespace, *, here: pathlib.Path, root: pathlib.Path) -> None:
    """Make every path in *args* absolute before the working directory changes.

    A path the user gave is relative to *here*, where the command was started; a path
    left out is the data root's own. A relative path that is missing under *here* but
    present under the data root is recorded in ``args.path_hints``, for the note
    :func:`_running_in` prints and the "did you mean" the error sites add.
    """
    hints: dict[str, tuple[str, pathlib.Path]] = {}
    args.path_hints = hints
    for name, default in _PATH_DEFAULTS.items():
        if not hasattr(args, name):
            continue
        value = getattr(args, name)
        setattr(args, name, root / default if value is None else _absolute(here, value))
        if value is not None and not pathlib.Path(value).expanduser().is_absolute():
            alternative = _absolute(root, value)
            if here != root and not getattr(args, name).exists() and alternative.exists():
                hints[name] = (str(value), alternative)
    if getattr(args, "lock_root", None):
        args.lock_root = str(_absolute(here, args.lock_root))


def _path_hint(args: argparse.Namespace, name: str) -> str:
    """ " (did you mean <data-root path>?)" for a relative path option that missed, else ``""``."""
    hint = getattr(args, "path_hints", {}).get(name)
    return f" (did you mean {hint[1]}?)" if hint else ""


def _appends_to(args: argparse.Namespace) -> pathlib.Path | None:
    """The ledger file *args*' command appends to, or ``None`` when it appends nothing."""
    if args.command == "void" or (args.command == "run" and not args.dry_run):
        return pathlib.Path(args.ledger_dir) / f"{args.bank}.jsonl"
    return None


@contextlib.contextmanager
def _running_in(root: _home.DataRoot, args: argparse.Namespace) -> Iterator[None]:
    """Run a command against *root*: paths anchored, any warning printed, the data root
    as the working directory, and the process state restored afterwards.

    The data root, and the task, scenario and ledger directories when they are given
    outside it, are withheld from every child fathom starts (an agent spawn, a gate): a
    variable naming one by value is dropped and PATH loses the entries in one
    (:func:`fathom.adapters.claude_cli.hidden_from_children`). Stripping by name alone
    misses VIRTUAL_ENV and PATH when fathom runs from a virtual environment inside the
    data root."""
    from fathom.adapters.claude_cli import hidden_from_children

    here = pathlib.Path.cwd()
    _anchor_paths(args, here=here, root=root.path)
    args.data_root = root.path
    warning = root.warning(appends_to=_appends_to(args))
    if warning:
        print(warning, file=sys.stderr)
    for name, (value, alternative) in args.path_hints.items():
        print(
            f"note: --{name.replace('_', '-')} {value} is relative to the working directory "
            f"({here}), where it does not exist; the data root has {alternative}. "
            "Pass that path, or run from the data root.",
            file=sys.stderr,
        )
    # An explicit stream directory is a path the user gave, so it is relative to `here`.
    saved_stream_dir = os.environ.get("FATHOM_STREAM_DIR")
    if saved_stream_dir:
        os.environ["FATHOM_STREAM_DIR"] = str(_absolute(here, saved_stream_dir))
    withheld = [root.path] + [
        pathlib.Path(getattr(args, name))
        for name in _PATH_DEFAULTS
        if getattr(args, name, None) is not None
    ]
    try:
        with (
            _fathom_home_withheld(),
            hidden_from_children(*withheld),
            contextlib.chdir(root.path),
        ):
            yield
    finally:
        if saved_stream_dir is None:
            os.environ.pop("FATHOM_STREAM_DIR", None)
        else:
            os.environ["FATHOM_STREAM_DIR"] = saved_stream_dir


@contextlib.contextmanager
def _fathom_home_withheld() -> Iterator[None]:
    """FATHOM_HOME unset while a command runs, and restored afterwards.

    The variable has done its work once the data root is resolved, and every agent spawn
    copies this process's environment. Left set, it would hand each trial's agent the path
    of the data root, which holds the task's reference solution and verifier.
    """
    saved = os.environ.pop(_home.ENV_VAR, None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ[_home.ENV_VAR] = saved


def _cmd_init(args: argparse.Namespace) -> int:
    """Create a data root; never overwrites a file."""
    here = pathlib.Path.cwd()
    if args.dir is not None:
        raw, option = args.dir, "DIR"
    else:
        raw, option = args.home, "--home"
    if raw is not None and not str(raw).strip():
        # An empty value is what a script's unset variable looks like; it does not mean
        # the working directory.
        print(
            f"error: {option} was given an empty value. Name the directory to create, or "
            "leave it out to create the data root in the working directory.",
            file=sys.stderr,
        )
        return 1
    target = _absolute(here, str(raw).strip()) if raw else pathlib.Path(os.path.abspath(here))
    problem = _home.init_problem(target)
    if problem is not None:
        print(f"error: {problem}", file=sys.stderr)
        return 1
    done = _home.init(target)
    print(f"fathom init: a data root at {target}")
    for name, created in done:
        print(f"  {'created' if created else 'kept   '}  {name}")
    missing = _home.missing_ignores(target)
    if missing:
        print(
            f"note: the existing .gitignore does not list {', '.join(missing)}; add "
            f"{'them' if len(missing) > 1 else 'it'} so runtime state and rendered scorecards "
            "stay out of commits."
        )
    for note in _home.init_notes(target):
        print(f"note: {note}")
    print(_init_next_steps())
    env_home = os.environ.get(_home.ENV_VAR, "").strip()
    if env_home and _absolute(here, env_home) != target:
        print(
            f"\nnote: FATHOM_HOME is set to {env_home}, and it takes precedence over the "
            f"working directory: commands run inside {target} use it until FATHOM_HOME is "
            f"set to {target} or unset. `fathom --home {target} <command>` works either way."
        )
    else:
        print(
            f"\nCommands run anywhere inside {target} find it on their own; from elsewhere, "
            f"pass --home {target} or set FATHOM_HOME={target}."
        )
    return EXIT_OK


# Where a user who installed the engine as a tool, with no copy of its repository, finds the
# authoring guide and the example data root.
_REPOSITORY_URL = "https://github.com/grimaldost/fathom"
_AUTHORING_GUIDE = "skills/fathom-eval/reference/authoring.md"
_EXAMPLE_ROOT = "examples/data-root"


def _release_ref() -> str:
    """The repository ref that matches the installed engine: its release tag, or ``main``
    when the version is not a plain release (a development build, or not installed)."""
    try:
        from importlib import metadata

        version = metadata.version("fathom")
    except Exception:
        return "main"
    parts = version.split(".")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        return f"v{version}"
    return "main"


def _init_next_steps() -> str:
    """What to do after ``fathom init``, with links to the guide and the example."""
    ref = _release_ref()
    guide = f"{_REPOSITORY_URL}/blob/{ref}/{_AUTHORING_GUIDE}"
    example = f"{_REPOSITORY_URL}/tree/{ref}/{_EXAMPLE_ROOT}"
    return (
        "\nNext steps:\n"
        "  1. Write a bank: tasks/<bank>/bank.toml (name, dataset_version, holdout), and one\n"
        "     directory per task holding task.toml, verify.py and fixtures/.\n"
        "  2. Write the arms as scenarios/<arm>.toml; the scorecard uses the arm named\n"
        '     "bare" as its anchor.\n'
        "  3. Check, for free, that the bank can tell arms apart:  fathom validate <bank>\n"
        "  4. Plan the matrix and its cost ceiling, spending nothing:\n"
        "     fathom run <bank> --dry-run\n"
        "  5. Before the first paid run, and again before each resume, check spawn isolation\n"
        "     on real spawns (spends a little):  fathom smoke --no-engine-boundary\n"
        "     (drop the flag once the data root has a scenarios/series.toml arm)\n"
        "The authoring guide covers every file a bank and an arm hold\n"
        f"({_AUTHORING_GUIDE} in the fathom repository):\n  {guide}\n"
        f"A complete small data root to copy from ({_EXAMPLE_ROOT}/ there):\n  {example}"
    )


def _cmd_index(args: argparse.Namespace) -> int:
    """Check or re-render the ledger index; free, spawns nothing."""
    from fathom import ledgerindex as _ledgerindex

    return _ledgerindex.run_index(args.home, write_index=args.write, command="fathom index")


def _cmd_run(args: argparse.Namespace) -> int:
    from fathom.scenario import load_scenario, resolve_scenario

    tasks_dir: pathlib.Path = args.tasks_dir if args.tasks_dir is not None else TASKS_DIR
    scenarios_dir: pathlib.Path = (
        args.scenarios_dir if args.scenarios_dir is not None else SCENARIOS_DIR
    )
    ledger_dir: pathlib.Path = args.ledger_dir or _ledger.LEDGER_DIR

    try:
        bank = load_bank(tasks_dir / args.bank)
    except Exception as exc:
        print(
            f"error: could not load bank '{args.bank}': {exc}{_path_hint(args, 'tasks_dir')}",
            file=sys.stderr,
        )
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
        print(
            f"error: no scenarios found in {scenarios_dir}{_path_hint(args, 'scenarios_dir')}",
            file=sys.stderr,
        )
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
    # quiet money bug this flag has caused before — so they are separate dests and the
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

    # Which data root this spends against, and appends to, before anything else is said.
    data_root = getattr(args, "data_root", None)
    if data_root is not None:
        print(f"data root: {data_root}")

    # --- Credential pre-flight: is this seat worth spending against at all? ---
    # Free, spawns nothing, reads two timestamps and never a token. It sits here
    # rather than inside `run_matrix` because it is a precondition of the INVOCATION,
    # not of the measurement: run_matrix's own gates (bank validity, arming) are about
    # whether the numbers would mean anything, and this one is about whether there
    # will be numbers. A dry run plans and spawns nothing, so it is exempt.
    if not args.dry_run and not args.skip_credential_check:
        from fathom.smoke import assert_credential_live, read_credential_status

        credential = assert_credential_live(read_credential_status())
        if not credential.ok:
            print(f"credential: {credential.detail}", file=sys.stderr)
            print(
                "REFUSING TO RUN: a matrix started on this seat would spawn and die on "
                "auth. Nothing is lost by fixing it first; re-invoke to continue from "
                "the ledger.",
                file=sys.stderr,
            )
            return EXIT_CREDENTIAL
        print(f"credential: {credential.detail}", file=sys.stderr)

    def _go(run_lock: Any | None) -> int:
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
            run_lock=run_lock,
        )

    # --- Run lock: one paid matrix per bank at a time (FATH-B53) --------------
    # A dry run spawns nothing and consumes no seat, so it queues for nothing.
    if args.dry_run or getattr(args, "no_lock", False):
        if getattr(args, "no_lock", False) and not args.dry_run:
            print(
                "WARNING: --no-lock: spending WITHOUT serializing against other runs "
                "of this bank on this seat",
                file=sys.stderr,
            )
        return _go(None)

    from fathom.runlock import LockTimeout, RunLock

    lock = RunLock(bank.name, label=f"fathom run {bank.name}")
    try:
        with lock.held(timeout_s=args.lock_wait_s, out=sys.stderr) as held:
            # A request left behind by an earlier run must not halt this one; the lock
            # scopes requests by time, and clearing here makes that visible in the tree.
            held.clear_stop_request()
            return _go(held)
    except LockTimeout as exc:
        print(f"lock: {exc}", file=sys.stderr)
        print(
            "REFUSING TO RUN: another run holds this bank. Wait, or `fathom stop "
            f"{bank.name}` to ask it to halt at its next trial boundary.",
            file=sys.stderr,
        )
        return EXIT_INFRASTRUCTURE


def _cmd_stop(args: argparse.Namespace) -> int:
    """Ask the run holding a bank's lock to stop; `--now` takes its process tree.

    Stopping only the process that started a run leaves `uv -> fathom -> claude` alive
    and spending. The request stops the matrix at the next trial boundary, and `--now`
    also terminates the holder's whole process tree.
    """
    import time as _time

    from fathom import runlock as _lock

    lock_root = pathlib.Path(args.lock_root) if args.lock_root else None
    now = _time.time()
    decision = _lock.holders(args.bank, lock_root=lock_root, now_s=now)

    if decision.holder is None:
        # Not an error: a stop that finds nothing to stop did its job.
        print(f"nothing holds the lock for bank {args.bank!r}")
        if decision.stale:
            print(
                f"({len(decision.stale)} stale ticket(s) past the "
                f"{_lock.STALE_AFTER_S:.0f}s horizon; the next run releases them)"
            )
        return EXIT_OK

    _lock.request_stop(args.bank, lock_root=lock_root, at_boundary=True, reason=args.reason)
    print(f"stop requested for bank {args.bank!r}, held by {decision.holder.describe(now)}")
    print(
        "the run halts after the trial in flight — the ledger is the checkpoint, so "
        "nothing already bought is lost"
    )

    if args.now:
        killed, detail = _lock.terminate_process_tree(decision.holder.pid)
        print(f"--now: terminating the holder's process tree: {detail}")
        if killed:
            print(
                "the in-flight trial's spend is discarded (it was not recorded); the "
                "holder's ticket expires on its own within "
                f"{_lock.STALE_AFTER_S:.0f}s"
            )
        else:
            print("the tree could not be terminated; the boundary request still stands")
    return EXIT_OK


def _load_resolved_scenarios(scenarios_dir: pathlib.Path) -> list[ResolvedScenario]:
    """Parse and resolve every arm in *scenarios_dir*, skipping unparsable files."""
    from fathom.scenario import load_scenario, resolve_scenario

    resolver = _DefaultResolver()
    out: list[ResolvedScenario] = []
    for sc_file in sorted(scenarios_dir.glob("*.toml")):
        try:
            out.append(resolve_scenario(load_scenario(sc_file), resolver))
        except Exception as exc:
            print(f"warning: skipping scenario {sc_file.name}: {exc}", file=sys.stderr)
    return out


def _note_stream_dir(scenarios_dir: pathlib.Path) -> None:
    """Say where `fathom run` will keep the streams of the arms that need them.

    An arm that declares a [context] inject or a non-default tool allowance is one
    whose stream is the only record of what its agent did (`_wants_stream_dir`).
    `fathom run` sets FATHOM_STREAM_DIR itself for exactly these arms, so `validate`
    prints a note saying where the streams go and that nothing needs doing — not a
    warning, which would ask the operator to act. Nothing is printed when
    FATHOM_STREAM_DIR is already set or no such arm is planned. Unparsable scenario
    files are skipped (as `_load_resolved_scenarios` already does for `run`), never
    turned into a validate failure.
    """
    if os.environ.get("FATHOM_STREAM_DIR"):
        return
    scenarios = _load_resolved_scenarios(scenarios_dir)
    streamed = [sc.name for sc in scenarios if _wants_stream_dir(sc)]
    if not streamed:
        return
    print(
        f"note: {len(streamed)} arm(s) in {scenarios_dir} declare a [context] inject or a "
        f"non-default tool allowance ({', '.join(streamed)}). `fathom run` keeps their "
        f"agents' streams under {_STREAM_ROOT.as_posix()}/<bank>/ in the data root; no "
        "action is needed. To keep them elsewhere, set FATHOM_STREAM_DIR."
    )


def _cmd_validate(args: argparse.Namespace) -> int:
    """Check the bank-validation triad. Free — local verifier runs, no spawns."""
    import fathom.validate as _validate

    tasks_dir = args.tasks_dir if args.tasks_dir is not None else TASKS_DIR
    try:
        bank = load_bank(tasks_dir / args.bank)
    except Exception as exc:
        print(
            f"error: could not load bank '{args.bank}': {exc}{_path_hint(args, 'tasks_dir')}",
            file=sys.stderr,
        )
        return 1

    checks = _validate.validate_bank(bank, stage_fn=stage_task, verifier_fn=run_verifier)
    print(_validate.render_validation(bank.name, checks))
    _note_stream_dir(args.scenarios_dir if args.scenarios_dir is not None else SCENARIOS_DIR)
    return EXIT_OK if _validate.validation_ok(checks, strict=args.strict) else EXIT_BANK_INVALID


def _cmd_verify_arming(args: argparse.Namespace) -> int:
    """Prove every declaring arm in a scenarios dir is armed, on real spawns."""
    from fathom.armingprobe import RealArmingProbe

    scenarios_dir = args.scenarios_dir if args.scenarios_dir is not None else SCENARIOS_DIR
    scenarios = _load_resolved_scenarios(scenarios_dir)
    if not scenarios:
        print(
            f"error: no scenarios found in {scenarios_dir}{_path_hint(args, 'scenarios_dir')}",
            file=sys.stderr,
        )
        return 1

    declaring = [sc for sc in scenarios if _arming.needs_verification(sc)]
    print(
        f"verify-arming: {len(scenarios)} arm(s) in {scenarios_dir}, "
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


def _warn_if_unpublished(bank: str, root: pathlib.Path | None = None) -> None:
    """Warn when a bank's conclusion is findable in neither a report nor STATUS.

    Rendering the scorecard is free and repeatable; publishing the verdict where a
    consumer can find it is the step that, left to prose, is skipped until conclusions
    survive only in commit messages, where nobody looking for them finds them (FATH-B06).

    ``docs/reports/LEDGER-INDEX.md`` does not count: it is generated, and names every
    bank that has a ledger whether or not anyone wrote the verdict up, so counting it
    would keep this warning from ever firing in a data root.

    *root* is the data root (default: the working directory). The warning is advisory:
    a data root that wants the rule to bind can hold a test of its own over its ledgers.
    """
    from fathom.ledgerindex import INDEX_PATH

    base = pathlib.Path.cwd() if root is None else pathlib.Path(root)
    reports_dir = base / INDEX_PATH.parent
    status = base / "docs" / "STATUS.md"
    try:
        in_report = any(
            bank in p.name or bank in p.read_text(encoding="utf-8", errors="replace")
            for p in reports_dir.glob("*.md")
            if p.name != INDEX_PATH.name
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
        voided_at=_dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
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
    """Render the scorecard, after checking that the bank has a ledger in the data root.

    ``fathom report`` reads ``ledger/<bank>.jsonl`` and writes ``report/scorecard-<bank>.md``
    in the data root (the working directory while a command runs). Without the ledger it
    would write a scorecard holding only its heading and exit 0, so a missing ledger is an
    error that names the path looked for.
    """
    import fathom.report as _report

    root = pathlib.Path.cwd()
    ledger_dir = root / _report.LEDGER_DIR
    ledger = ledger_dir / f"{args.bank}.jsonl"
    if not ledger.is_file():
        print(
            f"error: no ledger for bank '{args.bank}' at {ledger}, so there is nothing to render.",
            "This data root holds no ledger by that name; check the bank name.",
            sep="\n",
            file=sys.stderr,
        )
        return 1
    try:
        out_path = _report.render(
            args.bank,
            ledger_dir=ledger_dir,
            report_dir=root / _report.REPORT_DIR,
            tasks_dir=root / _report.TASKS_DIR,
        )
        print(f"report written to {out_path}")
        _warn_if_unpublished(args.bank, root)
        return EXIT_OK
    except Exception as exc:
        print(f"error rendering report: {exc}", file=sys.stderr)
        return 1


def _cmd_reconcile(args: argparse.Namespace) -> int:
    """Run the reconciliations; free, spawns nothing.

    Two failure directions, and the second is the one that keeps the gate honest: an
    unexcused discrepancy means two derivations of one fact disagree, and a *stale*
    exception means an excuse outlived the thing it excused.

    The root is a marked data root, found as every command finds one (``--home``,
    ``FATHOM_HOME``, the nearest marked directory at or above the working directory), or
    an engine checkout: named with ``--home``, or the working directory when no data root
    was named or found (:func:`fathom.ledgerindex.check_root`). Anything else is refused,
    because every check would pass on it for want of anything to compare.

    The refusal comes before any check runs, in the order ``fathom index`` uses: first the
    requested check names, then the root and its ``fathom.toml`` (a UTF-16 or malformed
    file is reported by its own message). The checks read every ledger and walk
    ``scenarios/``, so run first in a directory about to be refused, an unreadable ledger
    there would end in a traceback instead of the refusal.
    """
    from fathom import ledgerindex as _ledgerindex
    from fathom import reconcile as _reconcile

    if getattr(args, "list_checks", False):
        for check in _reconcile.CHECKS:
            print(f"{check.name:<24} {check.describe}")
        return EXIT_OK

    try:
        _reconcile.registry(args.checks)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNRECONCILED
    try:
        target = _ledgerindex.check_root(getattr(args, "home", None), command="fathom reconcile")
    except _ledgerindex.RootError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNRECONCILED
    if target.note:
        print(target.note, file=sys.stderr)
    root, kind = target.path, target.kind
    try:
        _reconcile.load_known(root)
    except _reconcile.KnownExceptionsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNRECONCILED
    try:
        outcome = _reconcile.run(root, names=args.checks)
    except (KeyError, _reconcile.KnownExceptionsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNRECONCILED

    bad = outcome.unexpected
    stale = outcome.stale

    print(f"reconciling the {kind} at {root}")
    for name, reason in outcome.skipped:
        print(f"[SKIPPED] {name}: {reason}")
    for d in bad:
        print(f"[DISAGREES] {d}")
    for fp in stale:
        print(
            f"[STALE EXCEPTION] {fp} no longer excuses anything — delete its "
            f"[[reconcile.known]] entry from {_reconcile.CONFIG_FILE}; an exception that "
            "outlives its discrepancy silently widens the gate"
        )

    have, total = _reconcile.preimage_coverage(root)
    if total:
        print(
            f"preimage coverage: {have}/{total} ledger rows ({100.0 * have / total:.0f}%) carry "
            "the second derivation the exact check needs. Rows written before 0.4.0 carry none; "
            "that is a coverage gap, reported rather than excused, and it only shrinks as "
            "trials are bought."
        )
    else:
        print("preimage coverage: no trial or run rows under ledger/ at this root.")
    print("")
    print(
        f"RECONCILE: {'OK' if outcome.ok else 'FAILED'} "
        f"({len(outcome.ran)} check(s) run, {len(outcome.skipped)} skipped, "
        f"{len(bad)} disagreement(s), {outcome.excused} excused, "
        f"{len(stale)} stale exception(s))"
    )
    return EXIT_OK if not bad and not stale else EXIT_UNRECONCILED


def _cmd_smoke(args: argparse.Namespace) -> int:
    """Run the smoke gate. Only its engine-boundary check reads data (the data root's
    series arm), so a data root is resolved for that check alone, and its absence is
    reported by that check rather than stopping the others."""
    from fathom.smoke import RealProbes, run_smoke

    include_engine = not args.no_engine_boundary
    root: _home.DataRoot | None = None
    if include_engine:
        try:
            root = _home.resolve(args.home)
        except _home.DataRootError as exc:
            if not exc.found_nothing:
                print(f"error: {exc}", file=sys.stderr)
                return 1
    if root is None:
        with _fathom_home_withheld():
            probes = RealProbes(scenarios_dir=None)
            return run_smoke(probes, force_fail=args.force_fail, include_engine=include_engine)
    with _running_in(root, args):
        probes = RealProbes(scenarios_dir=root.path / SCENARIOS_DIR)
        return run_smoke(probes, force_fail=args.force_fail, include_engine=include_engine)


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
        with open(plugin_json, encoding="utf-8") as f:
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
