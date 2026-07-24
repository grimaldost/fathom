"""CLI entry point — fathom run / report / smoke (spec §10)."""

from __future__ import annotations

import argparse
import dataclasses
import os
import pathlib
import sys
from typing import Any, Callable, TextIO

import fathom.ledger as _ledger
from fathom.grading.verifier import run_verifier
from fathom.scenario import ResolvedScenario
from fathom.taskbank import Bank, Task, load_bank, stage_task

_DEFAULT_REPEATS = 2
_DEFAULT_BASE_BRANCH = "main"
_CEILING_PER_TRIAL_USD = 2.00
SCENARIOS_DIR = pathlib.Path("scenarios")
TASKS_DIR = pathlib.Path("tasks")

# Named exit codes (spec §10)
EXIT_OK = 0
EXIT_INFRASTRUCTURE = 10


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
        "--max-budget-usd",
        type=float,
        default=None,
        dest="max_budget_usd",
        metavar="USD",
        help="Per-spawn budget cap (overrides the adapter default of 5.0); the real "
        "cost guard for a paid matrix (§11)",
    )

    report_p = sub.add_parser("report", help="Render a scorecard from the ledger")
    report_p.add_argument("bank", help="Bank name")

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
    ledger_dir: pathlib.Path | None = None,
    max_budget_usd: float | None = None,
    include_holdout: bool = False,
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
    ceiling_usd = num_planned * _CEILING_PER_TRIAL_USD

    # --- Print plan + ceiling BEFORE any spawn (spec §10 invariant) ---
    print(
        f"fathom run: bank={bank.name}  scenarios={len(resolved_scenarios)}"
        f"  tasks={len(tasks_to_run)}  repeats={repeats}",
        file=_out,
    )
    print(
        f"planned:  {num_planned} trials ({already_done} already done)"
        f"  ceiling: ${ceiling_usd:.2f}",
        file=_out,
    )

    if dry_run:
        print("[dry-run] no spawns", file=_out)
        return EXIT_OK

    if num_planned == 0:
        print("nothing to do", file=_out)
        return EXIT_OK

    _executor_factory = (
        executor_factory if executor_factory is not None else _default_executor_factory
    )
    if runner_factory is not None:
        _runner_factory = runner_factory
    else:

        def _runner_factory(sc: ResolvedScenario) -> Any:
            return _default_runner_factory(sc, max_budget_usd=max_budget_usd)

    # --- Execute trials (all spawns happen below this line) ---
    for sc, task, repeat in planned:
        # Names the raw-stream file the adapter tees when FATHOM_STREAM_DIR is
        # set (opt-in post-hoc analysis); harmless otherwise.
        os.environ["FATHOM_STREAM_TAG"] = f"{bank.name}--{sc.name}--{task.id}--r{repeat}"
        executor = _executor_factory(sc)
        runner = _runner_factory(sc)

        with _stage_fn(task, _DEFAULT_BASE_BRANCH) as workspace:
            trial_result = executor.run_trial(task, workspace, sc, runner)

            if trial_result.is_infrastructure:
                detail = trial_result.detail or "infrastructure error (auth or usage limit)"
                print(
                    f"infrastructure error: {detail} — stopping matrix",
                    file=_out,
                )
                # Ledger is the resume checkpoint — no writes for this trial.
                return EXIT_INFRASTRUCTURE

            # Grade the trial while workspace is still live (§7)
            verifier_data: dict[str, Any] | None = None
            verifier_errored = False
            verifier_note = ""
            if trial_result.scored:
                verify_entry = task.task_dir / task.verify["entry"]
                verify_timeout = int(task.verify.get("timeout_s", 60))
                vr = _verifier(verify_entry, workspace, timeout_s=verify_timeout)
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
                )
                _ledger.append_record(bank.name, ledger_run, ledger_dir=_ledger_dir)

            # Append trial record (with scenario + holdout for the report renderer).
            # A verifier error downgrades an otherwise-completed trial to errored so it
            # is never scored as a silent FAIL and is re-run on resume (spec §6).
            status_value = "errored" if verifier_errored else trial_result.status.value
            detail = "; ".join(p for p in (trial_result.detail, verifier_note) if p)
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
            )
            trial_dict = dataclasses.asdict(trial_rec)
            trial_dict["scenario"] = sc.name
            trial_dict["holdout"] = task.id in bank.holdout
            _ledger.append_record(bank.name, trial_dict, ledger_dir=_ledger_dir)

    return EXIT_OK


def _default_executor_factory(scenario: ResolvedScenario) -> Any:
    if scenario.strategy == "series":
        from fathom.strategies.series import SeriesExecutor

        return SeriesExecutor()
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
    if args.command == "smoke":
        return _cmd_smoke(args)
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

    return run_matrix(
        bank,
        resolved_scenarios,
        args.repeats,
        dry_run=args.dry_run,
        limit=args.limit,
        ledger_dir=ledger_dir,
        max_budget_usd=args.max_budget_usd,
        include_holdout=args.include_holdout,
    )


def _cmd_report(args: argparse.Namespace) -> int:
    import fathom.report as _report

    try:
        out_path = _report.render(args.bank)
        print(f"report written to {out_path}")
        return EXIT_OK
    except Exception as exc:
        print(f"error rendering report: {exc}", file=sys.stderr)
        return 1


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
