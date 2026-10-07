"""Tests for src/fathom/cli.py — stdlib-runnable.

Run via pytest or directly:  python tests/test_cli.py

All executors/runners/stage/verifier are stubbed — no real spawns.
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import types
import unittest
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

# A developer's own FATHOM_HOME must not steer the commands these tests run (in process,
# or as a subprocess that inherits the environment). tests/conftest.py does the same under
# pytest; this covers a bare run.
os.environ.pop("FATHOM_HOME", None)

import fathom.ledger as _ledger
from fathom.adapters.base import ExitStatus
from fathom.adapters.base import RunRecord as AdapterRunRecord
from fathom.cli import EXIT_INFRASTRUCTURE, EXIT_OK, run_matrix, void_trial
from fathom.grading.verifier import VerifierResult
from fathom.scenario import ContextConfig, LimitsOverride, ResolvedScenario, ToolsConfig
from fathom.strategies.base import PIN_STRONG, TrialResult, TrialStatus
from fathom.taskbank import Bank, Task, fixture_fingerprint

# ---------------------------------------------------------------------------
# Stub factories
# ---------------------------------------------------------------------------


def _make_scenario(name: str = "bare", config_hash: str = "a" * 64, **kw) -> ResolvedScenario:
    defaults: dict = {
        "adapter": "claude-cli",
        "model": "claude-opus-4-8",
        "strategy": "single-session",
        "effort": "high",
        "tools": ToolsConfig(source="none"),
        "limits": LimitsOverride(),
        "model_id": None,
        "tool_repo_sha": None,
        "tool_invocation_cmd": None,
    }
    defaults.update(kw)
    return ResolvedScenario(name=name, config_hash=config_hash, **defaults)


def _make_task(task_id: str, task_dir: Path) -> Task:
    return Task(
        id=task_id,
        instruction=f"do {task_id}",
        limits={},
        verify={"entry": "verify.py"},
        task_dir=task_dir,
    )


def _make_bank(name: str, tasks: list[Task], holdout: list[str] | None = None) -> Bank:
    return Bank(
        name=name,
        dataset_version="v1",
        tasks=tasks,
        holdout=holdout or [],
    )


def _ok_run() -> AdapterRunRecord:
    return AdapterRunRecord(
        status=ExitStatus.OK,
        tokens_in=100,
        tokens_out=50,
        num_turns=3,
        duration_s=10.0,
        cost_usd_est=0.05,
        cli_version="1.0",
        usage={"input_tokens": 100, "output_tokens": 50},
    )


def _ok_result() -> TrialResult:
    return TrialResult(
        status=TrialStatus.COMPLETED,
        runs=[_ok_run()],
        pin_level=PIN_STRONG,
        wall_clock_s=10.0,
    )


def _infra_result() -> TrialResult:
    return TrialResult(
        status=TrialStatus.INFRASTRUCTURE,
        runs=[],
        pin_level=PIN_STRONG,
        detail="usage limit reached",
    )


class StubExecutor:
    """Records run_trial calls and returns a configurable TrialResult."""

    def __init__(self, result_fn=None):
        self.calls: list = []
        self._result_fn = result_fn or (lambda task, ws, sc: _ok_result())

    def run_trial(self, task, workspace, scenario, runner):
        self.calls.append(types.SimpleNamespace(task=task, workspace=workspace, scenario=scenario))
        return self._result_fn(task, workspace, scenario)


class StubRunner:
    def execute(self, prompt, workspace, scenario):
        return _ok_run()


@contextmanager
def _stub_stage(task, base_branch):
    """Stub stage_task: yields a temp dir without git."""
    d = tempfile.mkdtemp(prefix="fathom-stub-ws-")
    try:
        yield Path(d)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _stub_verifier(verify_entry, workspace, timeout_s=60) -> VerifierResult:
    return VerifierResult(
        outcome="pass",
        criteria={"ok": True},
        stdout='{"ok": true}',
        stderr="",
        exit_code=0,
    )


def _run_matrix(bank, scenarios, repeats=2, **kw):
    """Helper: call run_matrix with stubs filled in and capture stdout.

    Bank validation is skipped by default: the stub verifier reports every
    fixture as already passing, which the FATH-B02 gate correctly refuses. Tests
    that are ABOUT that gate live in BankValidationGateTests and opt back in.
    """
    kw.setdefault("skip_bank_validation", True)
    kw.setdefault("executor_factory", lambda sc: StubExecutor())
    kw.setdefault("runner_factory", lambda sc: StubRunner())
    kw.setdefault("stage_task_fn", _stub_stage)
    kw.setdefault("verifier_fn", _stub_verifier)
    if "out" not in kw:
        kw["out"] = io.StringIO()
    out = kw["out"]
    code = run_matrix(bank, scenarios, repeats, **kw)
    return code, out.getvalue()


# ---------------------------------------------------------------------------
# Base test case: shared bank + scenarios + temp ledger
# ---------------------------------------------------------------------------


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        td = Path(self._tmp)
        self.task1 = _make_task("task-1", td)
        self.task2 = _make_task("task-2", td)
        self.bank = _make_bank("test-bank", [self.task1, self.task2])
        self.sc_a = _make_scenario("bare", config_hash="a" * 64)
        self.sc_b = _make_scenario("single-long", config_hash="b" * 64)
        self.scenarios = [self.sc_a, self.sc_b]
        self.ledger_dir = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)
        shutil.rmtree(str(self.ledger_dir), ignore_errors=True)


# ---------------------------------------------------------------------------
# Per-task verify timeout plumbing: a verifier that shells out to a separate
# environment's pytest can need longer than the default 60s to import and collect,
# so a task's `[verify] timeout_s` must reach the verifier.
# ---------------------------------------------------------------------------


class TestVerifyTimeout(_Base):
    @staticmethod
    def _recorder(sink):
        def _verifier(verify_entry, workspace, timeout_s=60):
            sink.append(timeout_s)
            return VerifierResult(
                outcome="pass", criteria={"ok": True}, stdout='{"ok": true}', stderr="", exit_code=0
            )

        return _verifier

    def test_task_verify_timeout_s_flows_to_verifier(self):
        received: list[int] = []
        slow_task = Task(
            id="slow",
            instruction="x",
            limits={},
            verify={"entry": "verify.py", "timeout_s": 180},
            task_dir=self.task1.task_dir,
        )
        _run_matrix(
            _make_bank("tb", [slow_task]),
            [self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
            verifier_fn=self._recorder(received),
        )
        self.assertEqual(received, [180])

    def test_default_verify_timeout_is_60(self):
        received: list[int] = []
        _run_matrix(
            self.bank,
            [self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
            verifier_fn=self._recorder(received),
        )
        self.assertTrue(received)
        self.assertTrue(all(t == 60 for t in received))


# ---------------------------------------------------------------------------
# §10 DoD 1: dry-run — counts + ceiling printed, zero spawns
# ---------------------------------------------------------------------------


class TestDryRun(_Base):
    def test_returns_ok(self):
        code, _ = _run_matrix(self.bank, self.scenarios, ledger_dir=self.ledger_dir, dry_run=True)
        self.assertEqual(code, EXIT_OK)

    def test_spawns_nothing(self):
        executor = StubExecutor()
        _run_matrix(
            self.bank,
            self.scenarios,
            ledger_dir=self.ledger_dir,
            dry_run=True,
            executor_factory=lambda sc: executor,
        )
        self.assertEqual(len(executor.calls), 0, "dry-run must not spawn anything")

    def test_prints_trial_count(self):
        # 2 scenarios × 2 tasks × 2 repeats = 8 planned
        _, output = _run_matrix(self.bank, self.scenarios, ledger_dir=self.ledger_dir, dry_run=True)
        self.assertIn("8 trials", output)

    def test_prints_the_arm_names(self):
        """The wrong --scenarios-dir with the same arm COUNT prints an identical count
        line, so the plan must say which arms it is about to buy."""
        _, output = _run_matrix(self.bank, self.scenarios, ledger_dir=self.ledger_dir, dry_run=True)
        self.assertIn("arms:", output)
        self.assertIn("bare", output)
        self.assertIn("single-long", output)
        # Verify config_hash prefix is shown for each arm
        self.assertIn(f"bare [{self.sc_a.config_hash[:12]}]", output)
        self.assertIn(f"single-long [{self.sc_b.config_hash[:12]}]", output)

    def test_prints_ceiling(self):
        _, output = _run_matrix(self.bank, self.scenarios, ledger_dir=self.ledger_dir, dry_run=True)
        self.assertIn("ceiling:", output)

    def test_the_ceiling_tracks_the_per_spawn_cap(self):
        """8 planned trials, cap $2/spawn -> $16.00; the default $5 cap -> $40.00."""
        _, capped = _run_matrix(
            self.bank,
            self.scenarios,
            ledger_dir=self.ledger_dir,
            dry_run=True,
            max_budget_usd=2.0,
        )
        self.assertIn("$16.00", capped)
        _, default = _run_matrix(
            self.bank, self.scenarios, ledger_dir=self.ledger_dir, dry_run=True
        )
        self.assertIn("$40.00", default)

    def test_raising_the_cap_raises_the_printed_ceiling(self):
        """The failure this replaces: --max-budget-usd 100 printed a $2/trial ceiling."""
        _, loosened = _run_matrix(
            self.bank,
            self.scenarios,
            ledger_dir=self.ledger_dir,
            dry_run=True,
            max_budget_usd=100.0,
        )
        self.assertIn("$800.00", loosened)

    def test_prints_dry_run_marker(self):
        _, output = _run_matrix(self.bank, self.scenarios, ledger_dir=self.ledger_dir, dry_run=True)
        self.assertIn("[dry-run]", output)


# ---------------------------------------------------------------------------
# The ceiling must be a CEILING for a multi-spawn strategy
#
# A flat one-spawn price per trial is wrong for `series`. A series trial spends one
# implementation spawn plus up to `max_fix_attempts` fix spawns for every PR in the
# decomposition (and review spawns when the review gate is blocking), and the
# per-spawn cap bounds each of those spawns individually, so a one-spawn price
# understates a 5-PR series arm many times over. An upfront number the run exceeds
# by an order of magnitude is worse than no number: the operator stops checking.
# ---------------------------------------------------------------------------


class TestSeriesCeiling(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.task_dir = Path(self._tmp)
        self.task = _make_task("t", self.task_dir)
        self.bank = _make_bank("b", [self.task])
        self.ledger_dir = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)
        shutil.rmtree(str(self.ledger_dir), ignore_errors=True)

    def _write_series(
        self, n_prs: int, max_fix_attempts: int | None = 2, blocking: bool | None = None
    ) -> None:
        body = "[series]\nid = 's'\nversion = '1'\n"
        if max_fix_attempts is not None or blocking is not None:
            body += "\n[review]\n"
        if max_fix_attempts is not None:
            body += f"max_fix_attempts = {max_fix_attempts}\n"
        if blocking is not None:
            body += f"blocking = {'true' if blocking else 'false'}\n"
        for i in range(n_prs):
            body += f"\n[[prs]]\nid = 'PR{i:02d}'\nbranch = 'b{i}'\nprompt = 'p{i}.md'\n"
        (self.task_dir / "series.toml").write_text(body, encoding="utf-8")

    def _plan(self, scenario, **kw) -> str:
        _, output = _run_matrix(
            self.bank, [scenario], repeats=1, ledger_dir=self.ledger_dir, dry_run=True, **kw
        )
        return output

    def test_series_ceiling_counts_every_pr_and_every_fix_attempt(self):
        self._write_series(5, max_fix_attempts=2)
        sc = _make_scenario("series-arm", config_hash="c" * 64, strategy="series")
        output = self._plan(sc, max_budget_usd=1.0)
        # 5 PRs x (1 impl + 2 fix) spawns x $1.00/spawn = $15.00 for the one trial.
        self.assertIn("ceiling: $15.00", output)

    def test_series_ceiling_shows_the_spawn_arithmetic(self):
        self._write_series(5, max_fix_attempts=2)
        sc = _make_scenario("series-arm", config_hash="c" * 64, strategy="series")
        output = self._plan(sc, max_budget_usd=1.0)
        self.assertIn("series arm series-arm/t", output)
        self.assertIn("5 PRs x (1 impl + 2 fix) spawns", output)

    def test_series_ceiling_uses_executor_defaults_without_a_rail(self):
        """No --max-budget-usd means the executor's own $20 impl / $3 fix are in force."""
        from fathom.strategies.series import DEFAULT_BUDGET_FIX, DEFAULT_BUDGET_IMPL

        self._write_series(5, max_fix_attempts=2)
        sc = _make_scenario("series-arm", config_hash="c" * 64, strategy="series")
        output = self._plan(sc)
        expected = 5 * (DEFAULT_BUDGET_IMPL + 2 * DEFAULT_BUDGET_FIX)
        self.assertIn(f"ceiling: ${expected:.2f}", output)

    def test_single_spawn_strategies_price_one_spawn_at_the_cap_in_force(self):
        """The series fix must not inflate every other arm's ceiling — one spawn stays one.

        The constant it used to assert against is gone, and deliberately: a
        single-spawn trial's worst case is ONE spawn at the cap that will actually
        bound it, not a fixed $2. `--max-budget-usd` is per-spawn, so passing a number
        LOOSENS the only runaway guard there is, and while the price was hardcoded the
        plan printed the same reassuring total either way, so a large loosening
        read as a tight rail. Both corrections live in
        `_trial_ceiling_usd`: spawns-per-trial (this test's original subject) and the
        cap in force (this assertion).
        """
        sc = _make_scenario("bare", config_hash="d" * 64, strategy="single-session")
        self.assertIn("ceiling: $1.00", self._plan(sc, max_budget_usd=1.0))
        self.assertNotIn("series arm", self._plan(sc, max_budget_usd=1.0))

    def test_a_single_spawn_ceiling_tracks_the_cap_rather_than_a_constant(self):
        """Raising the per-spawn cap must be visible in the plan, before the spend."""
        from fathom.cli import _DEFAULT_SPAWN_BUDGET_USD

        sc = _make_scenario("bare", config_hash="d" * 64, strategy="single-session")
        self.assertIn("ceiling: $50.00", self._plan(sc, max_budget_usd=50.0))
        self.assertIn(
            f"ceiling: ${_DEFAULT_SPAWN_BUDGET_USD:.2f}", self._plan(sc, max_budget_usd=None)
        )

    def test_unreadable_series_template_says_so_rather_than_quoting_a_number(self):
        """A missing template must not silently reinstate the understated rail."""
        sc = _make_scenario("series-arm", config_hash="c" * 64, strategy="series")
        output = self._plan(sc, max_budget_usd=1.0)  # no series.toml written
        self.assertIn("spawn count UNKNOWN", output)

    def test_missing_review_block_falls_back_to_the_engine_default(self):
        from fathom.cli import _SERIES_DEFAULT_MAX_FIX_ATTEMPTS

        self._write_series(3, max_fix_attempts=None)
        sc = _make_scenario("series-arm", config_hash="c" * 64, strategy="series")
        output = self._plan(sc, max_budget_usd=1.0)
        expected = 3 * (1 + _SERIES_DEFAULT_MAX_FIX_ATTEMPTS)
        self.assertIn(f"ceiling: ${expected:.2f}", output)

    # A blocking review gate adds review spawns: one before the first fix and one after
    # each fix, every one under the review budget the executor hands the engine. A
    # ceiling that leaves them out is not a worst case.

    def test_a_blocking_review_adds_a_review_spawn_per_round(self):
        self._write_series(5, max_fix_attempts=2, blocking=True)
        sc = _make_scenario("series-arm", config_hash="c" * 64, strategy="series")
        output = self._plan(sc, max_budget_usd=1.0)
        # 5 PRs x (1 impl + 2 fix + 3 review) spawns x $1.00/spawn = $30.00.
        self.assertIn("ceiling: $30.00", output)
        self.assertIn("5 PRs x (1 impl + 2 fix + 3 review) spawns", output)

    def test_a_blocking_review_is_priced_at_the_executor_review_budget(self):
        from fathom.strategies.series import (
            DEFAULT_BUDGET_FIX,
            DEFAULT_BUDGET_IMPL,
            DEFAULT_BUDGET_REVIEW,
        )

        self._write_series(5, max_fix_attempts=2, blocking=True)
        sc = _make_scenario("series-arm", config_hash="c" * 64, strategy="series")
        output = self._plan(sc)
        expected = 5 * (DEFAULT_BUDGET_IMPL + 2 * DEFAULT_BUDGET_FIX + 3 * DEFAULT_BUDGET_REVIEW)
        self.assertIn(f"ceiling: ${expected:.2f}", output)

    def test_a_non_blocking_review_adds_no_spawns(self):
        self._write_series(5, max_fix_attempts=2, blocking=False)
        sc = _make_scenario("series-arm", config_hash="c" * 64, strategy="series")
        output = self._plan(sc, max_budget_usd=1.0)
        self.assertIn("ceiling: $15.00", output)
        self.assertIn("5 PRs x (1 impl + 2 fix) spawns", output)


# ---------------------------------------------------------------------------
# §10 invariant: ceiling printed BEFORE first spawn
# ---------------------------------------------------------------------------


class TestCeilingBeforeSpawn(_Base):
    def test_ceiling_printed_before_first_spawn(self):
        out = io.StringIO()
        spawn_positions: list[int] = []

        def tracking_factory(sc):
            class _E:
                def run_trial(self, task, workspace, scenario, runner):
                    # Record stream position at spawn time
                    spawn_positions.append(out.tell())
                    return _ok_result()

            return _E()

        run_matrix(
            self.bank,
            [self.sc_a],
            1,  # 1 repeat → 2 spawns (2 tasks)
            executor_factory=tracking_factory,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
            out=out,
        )

        output = out.getvalue()
        ceiling_pos = output.find("ceiling:")
        self.assertGreater(ceiling_pos, -1, "ceiling line must appear in output")
        self.assertTrue(spawn_positions, "at least one spawn must have occurred")
        for pos in spawn_positions:
            self.assertLess(
                ceiling_pos,
                pos,
                f"spawn fired at stream pos {pos} before ceiling at {ceiling_pos}",
            )


# ---------------------------------------------------------------------------
# §10 DoD 2: --limit caps planned trials
# ---------------------------------------------------------------------------


class TestLimit(_Base):
    def test_limit_caps_spawns(self):
        calls: list[int] = []

        def counting_factory(sc):
            class _E:
                def run_trial(self, task, workspace, scenario, runner):
                    calls.append(1)
                    return _ok_result()

            return _E()

        # Full matrix: 2 scenarios × 2 tasks × 2 repeats = 8; cap at 3
        run_matrix(
            self.bank,
            self.scenarios,
            2,
            executor_factory=counting_factory,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            limit=3,
            ledger_dir=self.ledger_dir,
        )
        self.assertEqual(len(calls), 3, "--limit must cap the number of spawns")

    def test_limit_reflected_in_printed_plan(self):
        _, output = _run_matrix(
            self.bank,
            self.scenarios,
            dry_run=True,
            limit=3,
            ledger_dir=self.ledger_dir,
        )
        self.assertIn("3 trials", output)


# ---------------------------------------------------------------------------
# §10 DoD 2 (resume): completed ledger → zero planned trials
# ---------------------------------------------------------------------------


class TestResume(_Base):
    def _complete_all(self):
        """Write completed TrialRecords for every (sc, task, repeat) tuple."""
        for sc in self.scenarios:
            for task in [self.task1, self.task2]:
                for repeat in range(2):
                    rec = _ledger.TrialRecord(
                        bank=self.bank.name,
                        task_id=task.id,
                        repeat=repeat,
                        status="completed",
                        dataset_version=self.bank.dataset_version,
                        config_hash=sc.config_hash,
                        tool_git_sha="",
                        cli_version="",
                        pin_level="strong",
                    )
                    _ledger.append_record(self.bank.name, rec, ledger_dir=self.ledger_dir)

    def test_completed_ledger_plans_zero_trials(self):
        self._complete_all()
        executor = StubExecutor()
        _, output = _run_matrix(
            self.bank,
            self.scenarios,
            executor_factory=lambda sc: executor,
            ledger_dir=self.ledger_dir,
        )
        self.assertEqual(len(executor.calls), 0, "all completed → nothing to spawn")
        self.assertIn("0 trials", output)

    def test_partial_completion_skips_done_only(self):
        # Complete sc_a × task1 × repeat 0 and repeat 1 (2 of 8)
        for repeat in range(2):
            rec = _ledger.TrialRecord(
                bank=self.bank.name,
                task_id=self.task1.id,
                repeat=repeat,
                status="completed",
                dataset_version=self.bank.dataset_version,
                config_hash=self.sc_a.config_hash,
                tool_git_sha="",
                cli_version="",
                pin_level="strong",
            )
            _ledger.append_record(self.bank.name, rec, ledger_dir=self.ledger_dir)

        calls: list[int] = []

        def counting_factory(sc):
            class _E:
                def run_trial(self, task, workspace, scenario, runner):
                    calls.append(1)
                    return _ok_result()

            return _E()

        run_matrix(
            self.bank,
            self.scenarios,
            2,
            executor_factory=counting_factory,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        self.assertEqual(len(calls), 6, "8 total − 2 done = 6 spawns expected")


class TestFinishedBankPlan(_Base):
    """A finished bank's plan prices one more repeat (FATH-B82)."""

    def _complete(self, sc, task, repeat):
        rec = _ledger.TrialRecord(
            bank=self.bank.name,
            task_id=task.id,
            repeat=repeat,
            status="completed",
            dataset_version=self.bank.dataset_version,
            config_hash=sc.config_hash,
            tool_git_sha="",
            cli_version="",
            pin_level="strong",
        )
        _ledger.append_record(self.bank.name, rec, ledger_dir=self.ledger_dir)

    def _finished(self, repeats_done=3):
        """Two arms x one task, repeats 0..repeats_done-1 completed."""
        self.bank = _make_bank("test-bank", [self.task1])
        for sc in self.scenarios:
            for repeat in range(repeats_done):
                self._complete(sc, self.task1, repeat)

    def _plan(self, **kw):
        kw.setdefault("max_budget_usd", 0.5)
        return _run_matrix(self.bank, self.scenarios, repeats=2, ledger_dir=self.ledger_dir, **kw)

    def test_finished_bank_prices_one_more_repeat(self):
        self._finished()
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run):
                code, output = self._plan(dry_run=dry_run)
                self.assertEqual(code, 0)
                self.assertIn(
                    "one more repeat: ceiling $1.00 for 2 trials (one per arm and task); "
                    "plan it with --repeats 4",
                    output,
                )
                self.assertIn(
                    "completed in the ledger for these arms: 6 trials "
                    "(all repeats; the scorecard counts these)",
                    output,
                )
                tail = "[dry-run] no spawns" if dry_run else "nothing to do"
                self.assertLess(output.index("one more repeat"), output.index(tail))
                self.assertLess(output.index("planned:"), output.index("one more repeat"))

    def test_uneven_cells_say_at_least(self):
        self._finished()
        self._complete(self.sc_a, self.task1, 3)
        _, output = self._plan(dry_run=True)
        self.assertIn("at least one more repeat", output)
        self.assertIn("plan it with --repeats 5", output)
        self.assertIn("completed in the ledger for these arms: 7 trials", output)

    def test_counts_only_current_dataset_version_and_these_arms(self):
        self._finished()
        stale = _ledger.TrialRecord(
            bank=self.bank.name,
            task_id=self.task1.id,
            repeat=9,
            status="completed",
            dataset_version="older",
            config_hash=self.sc_a.config_hash,
            tool_git_sha="",
            cli_version="",
            pin_level="strong",
        )
        other_arm = _ledger.TrialRecord(
            bank=self.bank.name,
            task_id=self.task1.id,
            repeat=0,
            status="completed",
            dataset_version=self.bank.dataset_version,
            config_hash="c" * 64,
            tool_git_sha="",
            cli_version="",
            pin_level="strong",
        )
        for rec in (stale, other_arm):
            _ledger.append_record(self.bank.name, rec, ledger_dir=self.ledger_dir)
        _, output = self._plan(dry_run=True)
        self.assertIn("plan it with --repeats 4", output)
        self.assertIn("for these arms: 6 trials", output)

    def test_partially_done_ledger_prints_neither_line(self):
        self._finished(repeats_done=1)
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run):
                _, output = self._plan(dry_run=dry_run)
                self.assertNotIn("one more repeat", output)
                self.assertNotIn("completed in the ledger", output)


# ---------------------------------------------------------------------------
# §10 DoD 3: infrastructure error — clean stop, trial unscored, named status
# ---------------------------------------------------------------------------


class TestInfrastructureStop(_Base):
    def test_returns_named_exit_status(self):
        executor = StubExecutor(result_fn=lambda *_: _infra_result())
        code, output = _run_matrix(
            self.bank,
            [self.sc_a],
            1,
            executor_factory=lambda sc: executor,
            ledger_dir=self.ledger_dir,
        )
        self.assertEqual(
            code, EXIT_INFRASTRUCTURE, "infrastructure must return EXIT_INFRASTRUCTURE (10)"
        )
        self.assertIn("infrastructure error", output)

    def test_affected_trial_not_scored_in_ledger(self):
        executor = StubExecutor(result_fn=lambda *_: _infra_result())
        run_matrix(
            self.bank,
            [self.sc_a],
            1,
            executor_factory=lambda sc: executor,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        keys = _ledger.completed_keys(self.bank.name, ledger_dir=self.ledger_dir)
        self.assertEqual(len(keys), 0, "infra trial must not be recorded as completed")

    def test_matrix_stops_after_first_infra_error(self):
        """No further spawns after the first infrastructure result."""
        calls: list[int] = []

        def infra_first(task, workspace, scenario):
            calls.append(1)
            return _infra_result() if len(calls) == 1 else _ok_result()

        executor = StubExecutor(result_fn=infra_first)
        run_matrix(
            self.bank,
            [self.sc_a],
            2,  # 2 tasks × 2 repeats = 4 planned
            executor_factory=lambda sc: executor,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        self.assertEqual(len(calls), 1, "matrix must stop after first infra error")

    def test_ledger_untouched_as_resume_checkpoint(self):
        """Pre-populated ledger must not change when an infra error stops the run."""
        # Pre-populate with one completed trial
        pre_rec = _ledger.TrialRecord(
            bank=self.bank.name,
            task_id=self.task1.id,
            repeat=0,
            status="completed",
            dataset_version=self.bank.dataset_version,
            config_hash=self.sc_a.config_hash,
            tool_git_sha="",
            cli_version="",
            pin_level="strong",
        )
        _ledger.append_record(self.bank.name, pre_rec, ledger_dir=self.ledger_dir)
        ledger_path = self.ledger_dir / f"{self.bank.name}.jsonl"
        pre_content = ledger_path.read_text()

        # Now run sc_b (different config_hash → not yet done) with infra executor
        executor = StubExecutor(result_fn=lambda *_: _infra_result())
        run_matrix(
            self.bank,
            [self.sc_b],
            1,
            executor_factory=lambda sc: executor,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        post_content = ledger_path.read_text()
        self.assertEqual(pre_content, post_content, "ledger must be untouched after an infra stop")


# ---------------------------------------------------------------------------
# Normal run: ledger records written for completed trials
# ---------------------------------------------------------------------------


class TestLedgerWrites(_Base):
    def test_completed_trials_written_to_ledger(self):
        run_matrix(
            self.bank,
            [self.sc_a],
            1,  # 2 tasks × 1 repeat = 2 completed trials
            executor_factory=lambda sc: StubExecutor(),
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        keys = _ledger.completed_keys(self.bank.name, ledger_dir=self.ledger_dir)
        self.assertEqual(len(keys), 2, "both tasks must be recorded as completed")

    def test_run_record_persists_cost_usd_est(self):
        """The adapter record's cost_usd_est is carried into the ledger run record
        (§11 — the cost must not die at the ledger boundary)."""
        run_matrix(
            self.bank,
            [self.sc_a],
            1,
            executor_factory=lambda sc: StubExecutor(),  # _ok_run → cost_usd_est=0.05
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        run_recs = [
            r
            for r in _ledger.iter_records(self.bank.name, ledger_dir=self.ledger_dir)
            if isinstance(r, _ledger.RunRecord)
        ]
        self.assertTrue(run_recs, "expected at least one run record in the ledger")
        for r in run_recs:
            self.assertEqual(r.cost_usd_est, 0.05)

    def test_second_run_over_full_ledger_spawns_nothing(self):
        """A second identical run must see all trials as already done."""
        kw = {
            "executor_factory": lambda sc: StubExecutor(),
            "runner_factory": lambda sc: StubRunner(),
            "stage_task_fn": _stub_stage,
            "verifier_fn": _stub_verifier,
            "skip_bank_validation": True,
            "ledger_dir": self.ledger_dir,
        }
        run_matrix(self.bank, [self.sc_a], 1, **kw)

        executor = StubExecutor()
        run_matrix(
            self.bank,
            [self.sc_a],
            1,
            executor_factory=lambda sc: executor,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        self.assertEqual(len(executor.calls), 0, "second run must spawn nothing")


# ---------------------------------------------------------------------------
# Run rows name their arm: the scenario is provenance, the config_hash is identity
# ---------------------------------------------------------------------------


class TestRunRowsNameTheirScenario(_Base):
    def test_each_run_row_carries_the_name_of_the_arm_that_ran(self):
        _run_matrix(self.bank, self.scenarios, repeats=1, ledger_dir=self.ledger_dir)
        runs = [
            r
            for r in _ledger.iter_records(self.bank.name, ledger_dir=self.ledger_dir)
            if isinstance(r, _ledger.RunRecord)
        ]
        self.assertEqual(len(runs), 4, "two tasks x two arms, one run each")
        by_hash = {sc.config_hash: sc.name for sc in self.scenarios}
        for r in runs:
            self.assertEqual(r.scenario, by_hash[r.config_hash])
        self.assertEqual({r.scenario for r in runs}, {"bare", "single-long"})

    def test_identity_is_what_it_was_before_the_field(self):
        """The resume key and the hash on the rows come from the arm, not from scenario."""
        _run_matrix(self.bank, self.scenarios, repeats=1, ledger_dir=self.ledger_dir)
        expected = {
            (self.bank.name, "v1", task.id, sc.config_hash, 0)
            for task in (self.task1, self.task2)
            for sc in self.scenarios
        }
        self.assertEqual(
            _ledger.completed_keys(self.bank.name, ledger_dir=self.ledger_dir), expected
        )
        rows = [
            json.loads(line)
            for line in (self.ledger_dir / f"{self.bank.name}.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual({r["config_hash"] for r in rows}, {"a" * 64, "b" * 64})


# ---------------------------------------------------------------------------
# Holdout tasks excluded from run_matrix
# ---------------------------------------------------------------------------


class TestHoldout(_Base):
    def test_holdout_tasks_excluded_from_matrix(self):
        bank_with_holdout = _make_bank(
            "test-bank",
            [self.task1, self.task2],
            holdout=["task-2"],
        )
        calls: list[str] = []

        def capturing_factory(sc):
            class _E:
                def run_trial(self, task, workspace, scenario, runner):
                    calls.append(task.id)
                    return _ok_result()

            return _E()

        run_matrix(
            bank_with_holdout,
            [self.sc_a],
            1,
            executor_factory=capturing_factory,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        self.assertNotIn("task-2", calls, "holdout task must not be spawned")
        self.assertIn("task-1", calls)

    def test_include_holdout_runs_holdout_tasks(self):
        """--include-holdout makes ADR-0005's checkpoint mechanism executable: the
        sealed task runs, and its trials are marked holdout=True so the report's
        separate Holdout section can render them."""
        import json

        bank_with_holdout = _make_bank(
            "test-bank",
            [self.task1, self.task2],
            holdout=["task-2"],
        )
        calls: list[str] = []

        def capturing_factory(sc):
            class _E:
                def run_trial(self, task, workspace, scenario, runner):
                    calls.append(task.id)
                    return _ok_result()

            return _E()

        run_matrix(
            bank_with_holdout,
            [self.sc_a],
            1,
            executor_factory=capturing_factory,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
            include_holdout=True,
        )
        self.assertIn("task-2", calls, "--include-holdout must run the holdout task")
        self.assertIn("task-1", calls, "dev tasks still run alongside the holdout")
        raw = [
            json.loads(ln)
            for ln in (self.ledger_dir / "test-bank.jsonl").read_text().splitlines()
            if ln.strip()
        ]
        holdout_trials = [
            r for r in raw if r.get("kind") == "trial" and r.get("task_id") == "task-2"
        ]
        self.assertTrue(holdout_trials, "the holdout task must produce trial records")
        self.assertTrue(
            all(r.get("holdout") for r in holdout_trials),
            "holdout trials must carry holdout=True so the report's Holdout section renders",
        )


class TestRunnerFactoryInjection(unittest.TestCase):
    def _resolved(self, inject):
        from fathom.scenario import ContextConfig, LimitsOverride, ResolvedScenario, ToolsConfig

        return ResolvedScenario(
            name="nudge",
            adapter="claude-cli",
            model="m",
            strategy="single-session",
            effort="high",
            tools=ToolsConfig(source="none", allowed=("Read", "Write")),
            limits=LimitsOverride(),
            model_id=None,
            tool_repo_sha=None,
            tool_invocation_cmd=None,
            config_hash="x" * 64,
            context=ContextConfig(inject=inject),
        )

    def test_factory_passes_inject_to_runner(self):
        import tempfile

        from fathom.cli import _default_runner_factory

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as f:
            f.write("SKILL BODY")
            path = f.name
        runner = _default_runner_factory(self._resolved(path))
        self.assertEqual(runner.append_system_prompt_file, path)

    def test_factory_warns_on_missing_inject_file(self):
        import contextlib
        import io

        from fathom.cli import _default_runner_factory

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            _default_runner_factory(self._resolved("/no/such/skill.md"))
        self.assertIn("UN-SKILLED", buf.getvalue())


class TestRunnerFactoryMountPlumbing(unittest.TestCase):
    def _resolved_with_mounts(self, mounts: tuple) -> ResolvedScenario:
        from fathom.scenario import (
            ContextConfig,
            LimitsOverride,
            PluginsConfig,
            ResolvedScenario,
            ToolsConfig,
        )

        return ResolvedScenario(
            name="plugin-arm",
            adapter="claude-cli",
            model="m",
            strategy="single-session",
            effort="high",
            tools=ToolsConfig(source="none", allowed=("Read", "Write")),
            limits=LimitsOverride(),
            model_id=None,
            tool_repo_sha=None,
            tool_invocation_cmd=None,
            config_hash="y" * 64,
            context=ContextConfig(),
            plugins=PluginsConfig(mount=mounts),
        )

    def test_valid_mount_passes_dirs_to_runner(self):
        import tempfile

        from fathom.cli import _default_runner_factory

        with tempfile.TemporaryDirectory() as d:
            # A non-empty dir is a valid plugin mount
            Path(d, "plugin.json").write_text("{}", encoding="utf-8")
            runner = _default_runner_factory(self._resolved_with_mounts((d,)))
        self.assertEqual(runner.plugin_dirs, (d,))

    def test_valid_mount_produces_no_warning(self):
        import contextlib
        import tempfile

        from fathom.cli import _default_runner_factory

        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            Path(d, "plugin.json").write_text("{}", encoding="utf-8")
            with contextlib.redirect_stderr(buf):
                _default_runner_factory(self._resolved_with_mounts((d,)))
        self.assertNotIn("UNARMED", buf.getvalue())

    def test_missing_mount_dir_produces_warning(self):
        import contextlib

        from fathom.cli import _default_runner_factory

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            _default_runner_factory(self._resolved_with_mounts(("/no/such/plugin/dir",)))
        self.assertIn("UNARMED", buf.getvalue())
        self.assertIn("/no/such/plugin/dir", buf.getvalue())

    def test_empty_mount_dir_produces_warning(self):
        import contextlib
        import tempfile

        from fathom.cli import _default_runner_factory

        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(buf):
            # Directory exists but is empty — not a usable plugin mount
            _default_runner_factory(self._resolved_with_mounts((d,)))
        self.assertIn("UNARMED", buf.getvalue())

    def test_no_mounts_produces_no_warning_and_no_plugin_dirs(self):
        import contextlib

        from fathom.cli import _default_runner_factory

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            runner = _default_runner_factory(self._resolved_with_mounts(()))
        self.assertNotIn("UNARMED", buf.getvalue())
        self.assertEqual(runner.plugin_dirs, ())

    def test_missing_mount_dir_still_passed_to_runner(self):
        """Dirs reach the runner even when they're missing — the runner and CLI handle it."""
        import contextlib

        from fathom.cli import _default_runner_factory

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            runner = _default_runner_factory(self._resolved_with_mounts(("/no/such/plugin/dir",)))
        self.assertEqual(runner.plugin_dirs, ("/no/such/plugin/dir",))


class TestModelIdPersisted(_Base):
    """The exact CLI-reported model id (the 'strong pin', ADR-0001) must reach the
    ledger run record, not be dropped at the adapter->ledger boundary."""

    def test_model_id_carried_to_ledger(self):
        def _result_with_model(task, ws, sc):
            rec = AdapterRunRecord(
                status=ExitStatus.OK,
                tokens_in=1,
                tokens_out=1,
                num_turns=1,
                duration_s=1.0,
                cost_usd_est=0.0,
                model_id="claude-opus-4-8-20260115",
                cli_version="1.0",
                usage={},
            )
            return TrialResult(
                status=TrialStatus.COMPLETED, runs=[rec], pin_level=PIN_STRONG, wall_clock_s=1.0
            )

        run_matrix(
            self.bank,
            [self.sc_a],
            1,
            executor_factory=lambda sc: StubExecutor(result_fn=_result_with_model),
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        runs = [
            r
            for r in _ledger.iter_records(self.bank.name, ledger_dir=self.ledger_dir)
            if isinstance(r, _ledger.RunRecord)
        ]
        self.assertTrue(runs, "expected run records")
        for r in runs:
            self.assertEqual(
                r.model_id,
                "claude-opus-4-8-20260115",
                "the exact CLI-reported model id (strong pin) must be persisted",
            )


class TestVerifierErrorNotScoredAsFail(_Base):
    """A verifier crash/timeout/non-JSON must record an ERRORED trial, never a
    silent completed FAIL that occupies the resume key (spec §6)."""

    def _erroring_verifier(self, verify_entry, workspace, timeout_s=60):
        return VerifierResult(
            outcome="error",
            criteria=None,
            stdout="not json",
            stderr="verify.py raised",
            exit_code=1,
        )

    def test_verifier_error_records_errored_not_silent_fail(self):
        run_matrix(
            self.bank,
            [self.sc_a],
            1,
            executor_factory=lambda sc: StubExecutor(),  # the trial itself completes OK
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=self._erroring_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        trials = [
            r
            for r in _ledger.iter_records(self.bank.name, ledger_dir=self.ledger_dir)
            if isinstance(r, _ledger.TrialRecord)
        ]
        self.assertTrue(trials, "expected trial records")
        for t in trials:
            self.assertEqual(
                t.status,
                "errored",
                "a verifier crash must be recorded errored, not a silent completed FAIL",
            )
            self.assertIsNone(t.verifier_results, "no criteria on a verifier error")

    def test_verifier_error_does_not_occupy_resume_key(self):
        run_matrix(
            self.bank,
            [self.sc_a],
            1,
            executor_factory=lambda sc: StubExecutor(),
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=self._erroring_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
        keys = _ledger.completed_keys(self.bank.name, ledger_dir=self.ledger_dir)
        self.assertEqual(
            len(keys), 0, "a verifier-errored trial must be re-run on resume, not counted done"
        )


class TestModuleEntryPoint(unittest.TestCase):
    """`python -m fathom` is a shim-free entry point — works where the generated
    fathom.exe console script is blocked (Windows Application Control, os error 4551)."""

    def test_python_m_fathom_report_runs(self):
        import json
        import subprocess

        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            (dp / "ledger").mkdir()
            rec = {
                "kind": "trial",
                "bank": "toy",
                "task_id": "t1",
                "repeat": 0,
                "status": "completed",
                "dataset_version": "1",
                "config_hash": "h",
                "tool_git_sha": "",
                "cli_version": "",
                "pin_level": "strong",
                "verifier_results": {"ok": True},
                "scenario": "bare",
                "holdout": False,
            }
            (dp / "ledger" / "toy.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
            env = {**os.environ, "PYTHONPATH": str(pathlib.Path(__file__).parent.parent / "src")}
            proc = subprocess.run(
                [sys.executable, "-m", "fathom", "report", "toy"],
                cwd=str(dp),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(
                (dp / "report" / "scorecard-toy.md").exists(),
                "python -m fathom report must write the scorecard",
            )


class TestUnknownStrategyRejected(unittest.TestCase):
    """An unknown strategy string must be rejected, not silently run as single-session."""

    def _resolved(self, strategy: str) -> ResolvedScenario:
        from fathom.scenario import LimitsOverride, ToolsConfig

        return ResolvedScenario(
            name="typo-arm",
            adapter="claude-cli",
            model="m",
            strategy=strategy,
            effort="high",
            tools=ToolsConfig(source="none", allowed=("Read",)),
            limits=LimitsOverride(),
            model_id=None,
            tool_repo_sha=None,
            tool_invocation_cmd=None,
            config_hash="x" * 64,
        )

    def test_unknown_strategy_raises_naming_it(self):
        from fathom.cli import _default_executor_factory

        with self.assertRaises(ValueError) as cm:
            _default_executor_factory(self._resolved("gated-sesion"))  # typo of gated-session
        msg = str(cm.exception)
        self.assertIn("gated-sesion", msg, "error must name the offending strategy")
        self.assertIn("single-session", msg, "error should list the known strategies")

    def test_known_strategies_all_build(self):
        from fathom.cli import _default_executor_factory
        from fathom.strategies import KNOWN_STRATEGIES

        for strat in KNOWN_STRATEGIES:
            with self.subTest(strategy=strat):
                self.assertIsNotNone(_default_executor_factory(self._resolved(strat)))

    def test_series_arm_honours_the_max_budget_rail(self):
        """`--max-budget-usd` must reach the ENGINE's spawns, not only the adapter's.

        The series executor ignores the Runner (the engine spawns the CLI itself,
        ADR-0001), so capping the runner caps nothing on a series arm. Before this,
        the flag was silently inert there and the only ceiling in force was the
        executor's own $20/$5/$3 default — an operator who set a rail had one they
        did not have.
        """
        from fathom.cli import _default_executor_factory

        ex = _default_executor_factory(self._resolved("series"), max_budget_usd=2.0)
        self.assertEqual((ex.budget_impl, ex.budget_review, ex.budget_fix), (2.0, 2.0, 2.0))

    def test_series_arm_without_a_rail_keeps_the_recorded_defaults(self):
        """No flag means the executor's explicit, recorded defaults — not zero, not none."""
        from fathom.cli import _default_executor_factory
        from fathom.strategies.series import (
            DEFAULT_BUDGET_FIX,
            DEFAULT_BUDGET_IMPL,
            DEFAULT_BUDGET_REVIEW,
        )

        ex = _default_executor_factory(self._resolved("series"))
        self.assertEqual(
            (ex.budget_impl, ex.budget_review, ex.budget_fix),
            (DEFAULT_BUDGET_IMPL, DEFAULT_BUDGET_REVIEW, DEFAULT_BUDGET_FIX),
        )

    def test_dry_run_rejects_unknown_strategy(self):
        """--dry-run must catch a bad strategy up front (before planning/spawning)."""
        import contextlib
        import tempfile

        from fathom.cli import _cmd_run

        class _Args:
            command = "run"
            dry_run = True
            limit = None
            repeats = 1
            max_budget_usd = None

        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp)
            # Minimal bank
            bank_dir = tmp_p / "tasks" / "b"
            (bank_dir / "t1").mkdir(parents=True)
            (bank_dir / "bank.toml").write_text(
                'name = "b"\ndataset_version = "1"\nholdout = []\n', encoding="utf-8"
            )
            (bank_dir / "t1" / "task.toml").write_text(
                'id = "t1"\ninstruction = "x"\n[limits]\ntrial_timeout_s = 1\n'
                '[verify]\nentry = "verify.py"\n',
                encoding="utf-8",
            )
            (bank_dir / "t1" / "verify.py").write_text("print('{}')", encoding="utf-8")
            # Scenario with a typo'd strategy
            sc_dir = tmp_p / "scenarios"
            sc_dir.mkdir()
            (sc_dir / "arm.toml").write_text(
                'name = "arm"\nadapter = "claude-cli"\nmodel = "m"\n'
                'strategy = "gated-sesion"\neffort = "high"\n'
                '[tools]\nsource = "none"\nallowed = ["Read"]\n',
                encoding="utf-8",
            )
            args = _Args()
            args.bank = "b"
            args.tasks_dir = tmp_p / "tasks"
            args.scenarios_dir = sc_dir
            args.ledger_dir = tmp_p / "ledger"
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                code = _cmd_run(args)
            self.assertNotEqual(code, 0, "a bad strategy must make dry-run exit nonzero")
            self.assertIn("gated-sesion", buf.getvalue())


class ArmingGateTests(unittest.TestCase):
    """`fathom run` must refuse to spend on an arm it cannot prove armed (FATH-B01)."""

    class _Probe:
        """Stub arming probe returning a canned observation; counts its spawns."""

        def __init__(self, obs) -> None:
            self.obs = obs
            self.calls: list[str] = []

        def observe(self, scenario):
            self.calls.append(scenario.name)
            return self.obs

    @staticmethod
    def _obs(**kw):
        from fathom.arming import ArmingObservation

        base = {
            "spawn_ok": True,
            "init_present": True,
            "plugins": (),
            "skills": (),
            "tools": (),
            "mcp_servers": (),
            "hooks_fired": (),
            "successful_mcp_calls": (),
            "denied_tools": (),
            "argv": (),
            "spawn_env": {},
            "config_dir_files": (),
            "settings_sha": None,
        }
        base.update(kw)
        return ArmingObservation(**base)

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.bank = _make_bank("arming-bank", [_make_task("t1", Path(self._tmp))])
        self.ledger_dir = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
        shutil.rmtree(str(self.ledger_dir), ignore_errors=True)

    def _run(self, scenario, probe, **kw):
        executor = StubExecutor()
        code = run_matrix(
            self.bank,
            [scenario],
            1,
            executor_factory=lambda sc: executor,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
            arming_probe=probe,
            out=io.StringIO(),
            **kw,
        )
        return code, executor

    def test_an_unarmed_treatment_arm_blocks_the_matrix(self) -> None:
        from fathom.cli import EXIT_UNARMED
        from fathom.scenario import EnvConfig

        sc = _make_scenario(name="armed", env=EnvConfig(vars=(("FATHOM_MARK", "1"),)))
        probe = self._Probe(self._obs(spawn_env={}))  # var never reached the spawn
        code, executor = self._run(sc, probe)
        self.assertEqual(code, EXIT_UNARMED)
        self.assertEqual(
            executor.calls, [], "no trial may be spawned when arming verification fails"
        )

    def test_a_verified_treatment_arm_runs(self) -> None:
        from fathom.scenario import EnvConfig

        sc = _make_scenario(name="armed", env=EnvConfig(vars=(("FATHOM_MARK", "1"),)))
        probe = self._Probe(self._obs(spawn_env={"FATHOM_MARK": "1"}))
        code, executor = self._run(sc, probe)
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(executor.calls)

    def test_skip_arming_check_spends_anyway(self) -> None:
        from fathom.scenario import EnvConfig

        sc = _make_scenario(name="armed", env=EnvConfig(vars=(("FATHOM_MARK", "1"),)))
        probe = self._Probe(self._obs(spawn_env={}))
        code, executor = self._run(sc, probe, skip_arming_check=True)
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(executor.calls)
        self.assertEqual(probe.calls, [], "the override must not spawn a probe at all")

    def test_a_control_arm_is_never_probed(self) -> None:
        probe = self._Probe(self._obs())
        code, executor = self._run(_make_scenario(name="bare"), probe)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(probe.calls, [])
        self.assertTrue(executor.calls)

    def test_a_dry_run_never_probes(self) -> None:
        from fathom.scenario import EnvConfig

        sc = _make_scenario(name="armed", env=EnvConfig(vars=(("FATHOM_MARK", "1"),)))
        probe = self._Probe(self._obs(spawn_env={}))
        code, _ = self._run(sc, probe, dry_run=True)
        self.assertEqual(code, EXIT_OK, "planning spends nothing, so it needs no arming proof")
        self.assertEqual(probe.calls, [])


class UnrunTrialsAreStructurallyDistinctTests(_Base):
    """An un-run trial must not look like a real negative (FATH-B03).

    ``verifier_results`` was written whenever ``trial_result.scored`` was true —
    every status except INFRASTRUCTURE. Usage-limit casualties therefore
    landed as ``status="errored"`` carrying all-false criteria, structurally
    identical to a trial that ran and failed, and a reader who took them as real
    negatives depressed every affected arm's rate.

    Correctness must not depend on every reader independently remembering to
    filter on ``status``.
    """

    def _errored_executor(self):
        def _fn(task, workspace, scenario):
            return TrialResult(
                status=TrialStatus.ERRORED,
                runs=[_ok_run()],
                pin_level=PIN_STRONG,
                detail="usage limit reached mid-matrix",
            )

        return StubExecutor(_fn)

    def _trials(self, ledger_dir):
        """Read the raw on-disk JSONL — the shape external consumers actually see."""
        import json

        path = pathlib.Path(ledger_dir) / f"{self.bank.name}.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        return [r for r in rows if r.get("kind") == "trial"]

    def test_an_errored_trial_carries_no_criteria_dict(self) -> None:
        executor = self._errored_executor()
        _run_matrix(
            self.bank,
            [self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
            executor_factory=lambda sc: executor,
        )
        trials = self._trials(self.ledger_dir)
        self.assertTrue(trials)
        for t in trials:
            self.assertEqual(t["status"], "errored")
            self.assertIsNone(
                t["verifier_results"],
                "an errored trial must not emit criteria a reader can mistake for a "
                "measured failure",
            )

    def test_an_errored_trial_is_explicitly_marked_invalid(self) -> None:
        executor = self._errored_executor()
        _run_matrix(
            self.bank,
            [self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
            executor_factory=lambda sc: executor,
        )
        for t in self._trials(self.ledger_dir):
            self.assertIs(t.get("valid"), False)

    def test_a_completed_trial_keeps_its_criteria_and_is_valid(self) -> None:
        _run_matrix(
            self.bank,
            [self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
        )
        trials = self._trials(self.ledger_dir)
        self.assertTrue(trials)
        for t in trials:
            self.assertEqual(t["status"], "completed")
            self.assertEqual(t["verifier_results"], {"ok": True})
            self.assertIs(t.get("valid"), True)


class VerifierEvidenceIsRetainedTests(_Base):
    """A trial must not destroy the evidence needed to diagnose it (FATH-B14).

    `VerifierResult` already carries `stdout` and `stderr`, and both are in hand at
    the ledger write site — they were simply dropped. So a failing criterion could
    not be diagnosed without re-running the trial, and a verifier that crashed took
    its own error message with it.

    A verifier that imports the agent's modified package is the usual case: anything
    that package prints at import time lands on the verifier's stdout ahead of the JSON,
    the trial is scored `verifier error: non-JSON/crash`, and without the output the
    reason cannot be recovered.
    """

    def _crashing_verifier(self, stdout: str, stderr: str = ""):
        def _fn(entry, workspace, timeout_s=60):
            return VerifierResult(
                outcome="error", criteria=None, stdout=stdout, stderr=stderr, exit_code=1
            )

        return _fn

    def _trials(self):
        import json

        path = pathlib.Path(self.ledger_dir) / f"{self.bank.name}.jsonl"
        rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
        return [r for r in rows if r.get("kind") == "trial"]

    def test_a_crashed_verifiers_output_is_persisted(self) -> None:
        noise = "Loading package config...\n" + '{"src-layout": true}'
        _run_matrix(
            self.bank,
            [self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
            verifier_fn=self._crashing_verifier(noise, "Traceback: boom"),
        )
        trials = self._trials()
        self.assertTrue(trials)
        for t in trials:
            self.assertIn("Loading package config", t.get("verifier_stdout", ""))
            self.assertIn("boom", t.get("verifier_stderr", ""))

    def test_a_completed_trials_verifier_stdout_is_persisted(self) -> None:
        _run_matrix(self.bank, [self.sc_a], repeats=1, ledger_dir=self.ledger_dir)
        for t in self._trials():
            self.assertEqual(t["status"], "completed")
            self.assertIn("ok", t.get("verifier_stdout", ""))

    def test_persisted_output_is_bounded(self) -> None:
        # The ledger is committed; an unbounded blob would put a megabyte of agent
        # output into git history on one bad trial.
        _run_matrix(
            self.bank,
            [self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
            verifier_fn=self._crashing_verifier("x" * 50_000, "y" * 50_000),
        )
        for t in self._trials():
            self.assertLessEqual(len(t.get("verifier_stdout", "")), 4096)
            self.assertLessEqual(len(t.get("verifier_stderr", "")), 4096)


class BankValidationGateTests(unittest.TestCase):
    """`fathom run` must refuse to spend on a bank that cannot discriminate (FATH-B02)."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.bank = _make_bank("valid-bank", [_make_task("t1", Path(self._tmp))])
        self.ledger_dir = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
        shutil.rmtree(str(self.ledger_dir), ignore_errors=True)

    @staticmethod
    def _verifier(outcome: str):
        def _fn(entry, workspace, timeout_s=60):
            return VerifierResult(
                outcome=outcome,
                criteria={"ok": outcome == "pass"},
                stdout="{}",
                stderr="",
                exit_code=0 if outcome == "pass" else 1,
            )

        return _fn

    def _run(self, outcome: str, **kw):
        executor = StubExecutor()
        code = run_matrix(
            self.bank,
            [_make_scenario(name="bare")],
            1,
            executor_factory=lambda sc: executor,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=self._verifier(outcome),
            ledger_dir=self.ledger_dir,
            out=io.StringIO(),
            **kw,
        )
        return code, executor

    def test_a_bank_whose_verifier_already_passes_blocks_the_matrix(self) -> None:
        from fathom.cli import EXIT_BANK_INVALID

        code, executor = self._run("pass")
        self.assertEqual(code, EXIT_BANK_INVALID)
        self.assertEqual(
            executor.calls, [], "a non-discriminating bank must cost nothing to discover"
        )

    def test_a_discriminating_bank_runs(self) -> None:
        code, executor = self._run("fail")
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(executor.calls)

    def test_skip_bank_validation_spends_anyway(self) -> None:
        code, executor = self._run("pass", skip_bank_validation=True)
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(executor.calls)

    def test_a_dry_run_is_not_blocked(self) -> None:
        code, _ = self._run("pass", dry_run=True)
        self.assertEqual(code, EXIT_OK, "planning spends nothing")

    def _run_probe_arm(self) -> tuple[int, StubExecutor, str]:
        from fathom.scenario import GateConfig

        executor = StubExecutor()
        out = io.StringIO()
        arm = _make_scenario(
            name="probe-arm",
            strategy="gated-session",
            gate=GateConfig(extra=("python ${task_dir}/probe.py",)),
        )
        code = run_matrix(
            self.bank,
            [arm],
            1,
            executor_factory=lambda sc: executor,
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=self._verifier("fail"),
            ledger_dir=self.ledger_dir,
            out=out,
        )
        return code, executor, out.getvalue()

    def test_an_arm_extra_naming_a_missing_script_blocks_the_matrix(self) -> None:
        # FATH-B54: a gate that could never have run is a broken arm, found before the spend.
        from fathom.cli import EXIT_BANK_INVALID

        code, executor, out = self._run_probe_arm()
        self.assertEqual(code, EXIT_BANK_INVALID, out)
        self.assertEqual(executor.calls, [], "a dangling gate path must cost nothing to discover")
        self.assertIn("${task_dir}/probe.py", out)
        self.assertIn("probe-arm", out)

    def test_the_same_arm_runs_once_the_script_exists(self) -> None:
        (Path(self._tmp) / "probe.py").write_text("", encoding="utf-8")
        code, executor, out = self._run_probe_arm()
        self.assertEqual(code, EXIT_OK, out)
        self.assertTrue(executor.calls)


# ---------------------------------------------------------------------------
# --tasks: buy a screen before the full matrix
# ---------------------------------------------------------------------------


class TestTaskFilter(_Base):
    """Staging by TASK, which --limit cannot express.

    The plan is scenario-major, so --limit cuts whole arms off the end of it — it
    can shorten a matrix but cannot select the rungs a screen needs to ask about
    (one band, or a positive control, at higher repeats). Without this, "screen the
    mid band before paying for the mid arm" is not a command anyone can type.
    """

    def _calls(self, **kw) -> list[str]:
        calls: list[str] = []

        def capturing_factory(sc):
            class _E:
                def run_trial(self, task, workspace, scenario, runner):
                    calls.append(task.id)
                    return _ok_result()

            return _E()

        _run_matrix(
            kw.pop("bank", self.bank),
            [self.sc_a],
            kw.pop("repeats", 1),
            ledger_dir=self.ledger_dir,
            executor_factory=capturing_factory,
            **kw,
        )
        return calls

    def test_only_the_named_tasks_run(self):
        self.assertEqual(self._calls(task_ids=["task-2"]), ["task-2"])

    def test_omitting_the_filter_runs_everything(self):
        self.assertEqual(sorted(self._calls()), ["task-1", "task-2"])

    def test_duplicates_do_not_duplicate_trials(self):
        self.assertEqual(self._calls(task_ids=["task-1", "task-1"]), ["task-1"])

    def test_an_unknown_id_is_an_error_not_an_empty_run(self):
        """A typo that silently runs nothing is a wasted stage and a false 'done'."""
        err = io.StringIO()
        with _capture_stderr(err):
            code, output = _run_matrix(
                self.bank,
                [self.sc_a],
                1,
                ledger_dir=self.ledger_dir,
                task_ids=["task-1", "taks-2"],
            )
        self.assertNotEqual(code, EXIT_OK)
        self.assertIn("taks-2", err.getvalue())
        self.assertNotIn("planned:", output, "nothing may be planned on a bad filter")

    def test_it_cannot_be_used_to_unseal_a_holdout(self):
        """Spending a holdout stays an --include-holdout decision the ledger records."""
        err = io.StringIO()
        sealed = _make_bank("test-bank", [self.task1, self.task2], holdout=["task-2"])
        with _capture_stderr(err):
            code, _ = _run_matrix(
                sealed,
                [self.sc_a],
                1,
                ledger_dir=self.ledger_dir,
                task_ids=["task-2"],
            )
        self.assertNotEqual(code, EXIT_OK)
        self.assertIn("--include-holdout", err.getvalue())

    def test_the_plan_line_reports_the_filtered_task_count(self):
        _, output = _run_matrix(
            self.bank,
            self.scenarios,
            2,
            ledger_dir=self.ledger_dir,
            dry_run=True,
            task_ids=["task-1"],
        )
        self.assertIn("tasks=1", output)
        self.assertIn("4 trials", output)  # 2 scenarios x 1 task x 2 repeats


@contextmanager
def _capture_stderr(sink):
    original, sys.stderr = sys.stderr, sink
    try:
        yield
    finally:
        sys.stderr = original


class SpendRailTests(unittest.TestCase):
    """The per-invocation rail halts before buying the next trial.

    It is deliberately NOT summed from the ledger: `fathom run` is resumable, so a
    ledger-sourced total holds every prior invocation's spend and would trip at $0 of new
    spend on a resume — the same shape as a per-spawn cap that reads like a program rail.
    """

    def setUp(self):
        self.ledger_dir = pathlib.Path(tempfile.mkdtemp())
        td = pathlib.Path(tempfile.mkdtemp())
        self.bank = _make_bank("rail", [_make_task("t1", td), _make_task("t2", td)])
        self.sc = _make_scenario("bare")

    def test_a_reached_rail_halts_before_the_next_trial(self):
        from fathom.cli import EXIT_RUN_BUDGET

        class _Boom:
            def run_trial(self, *a, **k):
                raise AssertionError("a trial ran after the budget was already reached")

        code, out = _run_matrix(
            self.bank,
            [self.sc],
            repeats=1,
            ledger_dir=self.ledger_dir,
            max_run_usd=0.0,
            executor_factory=lambda sc: _Boom(),
        )
        self.assertEqual(code, EXIT_RUN_BUDGET)
        self.assertIn("run budget reached", out)

    def test_no_rail_means_no_halt(self):
        """The rail must be opt-in; absent, the matrix runs to completion as before."""
        code, _ = _run_matrix(self.bank, [self.sc], repeats=1, ledger_dir=self.ledger_dir)
        self.assertEqual(code, 0)

    def test_a_generous_rail_does_not_halt(self):
        code, out = _run_matrix(
            self.bank, [self.sc], repeats=1, ledger_dir=self.ledger_dir, max_run_usd=10_000.0
        )
        self.assertEqual(code, 0)
        self.assertNotIn("run budget reached", out)


# ---------------------------------------------------------------------------
# Fixture integrity guard and void rows in run_matrix
# ---------------------------------------------------------------------------


class FixtureGuardTests(_Base):
    def _fixture_task(self, name: str = "fx") -> Task:
        root = Path(self._tmp) / name
        (root / "fixtures" / "pkg").mkdir(parents=True)
        (root / "fixtures" / "pkg" / "a.py").write_text("print(1)\n", encoding="utf-8")
        return Task(
            id=name, instruction="x", limits={}, verify={"entry": "verify.py"}, task_dir=root
        )

    def test_every_trial_row_records_the_fixture_sha(self):
        task = self._fixture_task()
        code, _ = _run_matrix(
            _make_bank("tb", [task]), [self.sc_a], repeats=1, ledger_dir=self.ledger_dir
        )
        self.assertEqual(code, EXIT_OK)
        rows = [
            json.loads(line)
            for line in (self.ledger_dir / "tb.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        trial = next(r for r in rows if r["kind"] == "trial")
        self.assertEqual(trial["fixture_sha"], fixture_fingerprint(task))

    def test_drift_before_staging_stops_the_matrix_without_spend(self):
        task = self._fixture_task()
        mutating_stage = _mutating_stage_factory(task, when="before")
        code, out = _run_matrix(
            _make_bank("tb", [task]),
            [self.sc_a],
            repeats=2,
            ledger_dir=self.ledger_dir,
            stage_task_fn=mutating_stage,
        )
        self.assertEqual(code, EXIT_INFRASTRUCTURE)
        self.assertIn("fixture drift", out)
        rows = [
            json.loads(line)
            for line in (self.ledger_dir / "tb.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        # The first trial ran and was recorded; the mutation happened during it, so it
        # is errored (not scored) and nothing after it was bought.
        trials = [r for r in rows if r["kind"] == "trial"]
        self.assertEqual(len(trials), 1)
        self.assertEqual(trials[0]["status"], "errored")
        self.assertIn("fixture drift during trial", trials[0]["detail"])
        self.assertFalse(trials[0]["valid"])

    def test_a_voided_trial_is_planned_again_and_its_rerun_counts(self):
        task = self._fixture_task()
        bank = _make_bank("tb", [task])
        code, _ = _run_matrix(bank, [self.sc_a], repeats=1, ledger_dir=self.ledger_dir)
        self.assertEqual(code, EXIT_OK)
        code, out = _run_matrix(bank, [self.sc_a], repeats=1, ledger_dir=self.ledger_dir)
        self.assertIn("planned:  0 trials (1 already done)", out)
        void = void_trial(
            "tb", "bare", 0, "fixture drift", evidence="test", ledger_dir=self.ledger_dir
        )
        self.assertEqual(void.config_hash, "a" * 64)
        code, out = _run_matrix(bank, [self.sc_a], repeats=1, ledger_dir=self.ledger_dir)
        self.assertIn("planned:  1 trials (0 already done)", out)
        self.assertEqual(code, EXIT_OK)
        code, out = _run_matrix(bank, [self.sc_a], repeats=1, ledger_dir=self.ledger_dir)
        self.assertIn("planned:  0 trials (1 already done)", out)
        with self.assertRaises(LookupError):
            void_trial("tb", "nope", 0, "r", ledger_dir=self.ledger_dir)


def _mutating_stage_factory(task: Task, when: str):
    """A stage stub that edits the task's fixture while the first trial is live."""
    state = {"count": 0}

    @contextmanager
    def _stage(t, base_branch):
        d = tempfile.mkdtemp(prefix="fathom-stub-ws-")
        try:
            state["count"] += 1
            if state["count"] == 1:
                (task.task_dir / "fixtures" / "pkg" / "a.py").write_text(
                    "print('solution')\n", encoding="utf-8"
                )
            yield Path(d)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    return _stage


class CredentialPreflightTests(unittest.TestCase):
    """`fathom run` refuses a seat with no credential life left (FATH-B04).

    Free and spawn-free: the check reads two timestamps out of the credential file
    and never a token. Without it a matrix starts, spawns, and dies on auth, and does
    so again on every retry.
    """

    def _bank_tree(self, tmp_p: pathlib.Path) -> None:
        bank_dir = tmp_p / "tasks" / "b"
        (bank_dir / "t1").mkdir(parents=True)
        (bank_dir / "bank.toml").write_text(
            'name = "b"\ndataset_version = "1"\nholdout = []\n', encoding="utf-8"
        )
        (bank_dir / "t1" / "task.toml").write_text(
            'id = "t1"\ninstruction = "x"\n[limits]\ntrial_timeout_s = 1\n'
            '[verify]\nentry = "verify.py"\n',
            encoding="utf-8",
        )
        (bank_dir / "t1" / "verify.py").write_text("print('{}')", encoding="utf-8")
        sc_dir = tmp_p / "scenarios"
        sc_dir.mkdir()
        (sc_dir / "arm.toml").write_text(
            'name = "arm"\nadapter = "claude-cli"\nmodel = "m"\n'
            'strategy = "single-session"\neffort = "high"\n'
            '[tools]\nsource = "none"\nallowed = ["Read"]\n',
            encoding="utf-8",
        )

    def _args(self, tmp_p: pathlib.Path, **kw):
        args = types.SimpleNamespace(
            command="run",
            bank="b",
            dry_run=False,
            limit=None,
            tasks=None,
            repeats=1,
            tasks_dir=tmp_p / "tasks",
            scenarios_dir=tmp_p / "scenarios",
            ledger_dir=tmp_p / "ledger",
            include_holdout=False,
            max_spawn_usd=None,
            legacy_max_budget_usd=None,
            max_run_usd=None,
            skip_bank_validation=True,
            skip_arming_check=True,
            skip_credential_check=False,
            # These tests are about the credential gate, not the lock: --no-lock keeps
            # them out of the repo's own lock directory entirely.
            no_lock=True,
            lock_wait_s=None,
        )
        for k, v in kw.items():
            setattr(args, k, v)
        return args

    def _run(self, args, credential):
        import contextlib

        import fathom.smoke as _smoke
        from fathom.cli import _cmd_run

        real = _smoke.read_credential_status
        _smoke.read_credential_status = lambda *a, **kw: credential
        buf = io.StringIO()
        try:
            with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(io.StringIO()):
                code = _cmd_run(args)
        finally:
            _smoke.read_credential_status = real
        return code, buf.getvalue()

    @staticmethod
    def _credential(**kw):
        import time

        from fathom.smoke import CredentialStatus

        now = time.time()
        base = {
            "found": True,
            "readable": True,
            "expires_at_ms": int((now + 3600) * 1000),
            "refresh_expires_at_ms": int((now + 30 * 86400) * 1000),
        }
        base.update(kw)
        return CredentialStatus(**base)

    def test_dead_credential_refuses_before_any_spawn(self):
        import time

        from fathom.cli import EXIT_CREDENTIAL

        dead = self._credential(
            expires_at_ms=int((time.time() - 86400) * 1000),
            refresh_expires_at_ms=int((time.time() - 3600) * 1000),
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp)
            self._bank_tree(tmp_p)
            code, err = self._run(self._args(tmp_p), dead)
        self.assertEqual(code, EXIT_CREDENTIAL)
        self.assertIn("re-authenticate", err.lower())
        self.assertIn("REFUSING TO RUN", err)

    def test_missing_credential_file_refuses_rather_than_passing_by_absence(self):
        from fathom.cli import EXIT_CREDENTIAL
        from fathom.smoke import CredentialStatus

        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp)
            self._bank_tree(tmp_p)
            code, _ = self._run(
                self._args(tmp_p), CredentialStatus(found=False, readable=False, detail="gone")
            )
        self.assertEqual(code, EXIT_CREDENTIAL)

    def test_dry_run_is_exempt(self):
        """A dry run spawns nothing, so it has nothing to authenticate."""
        import time

        dead = self._credential(
            expires_at_ms=int((time.time() - 86400) * 1000),
            refresh_expires_at_ms=int((time.time() - 3600) * 1000),
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp)
            self._bank_tree(tmp_p)
            code, _ = self._run(self._args(tmp_p, dry_run=True), dead)
        self.assertEqual(code, EXIT_OK)

    def test_skip_flag_lets_a_dead_credential_through(self):
        import time

        dead = self._credential(
            expires_at_ms=int((time.time() - 86400) * 1000),
            refresh_expires_at_ms=int((time.time() - 3600) * 1000),
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = pathlib.Path(tmp)
            self._bank_tree(tmp_p)
            # --limit 0 plans nothing, so the matrix returns before any spawn: this
            # test is about the gate NOT firing, and must never buy a trial to say so.
            args = self._args(tmp_p, skip_credential_check=True, limit=0)
            code, err = self._run(args, dead)
        self.assertEqual(code, EXIT_OK)
        self.assertNotIn("REFUSING TO RUN", err)


class StopVerbTests(unittest.TestCase):
    """`fathom stop` halts a matrix at its next trial boundary (FATH-B53).

    It halts BETWEEN trials because the ledger is the checkpoint: nothing already bought
    is lost, and no paid spawn is thrown away.
    """

    def setUp(self):
        self.ledger_dir = pathlib.Path(tempfile.mkdtemp())
        self.lock_root = pathlib.Path(tempfile.mkdtemp())
        td = pathlib.Path(tempfile.mkdtemp())
        self.bank = _make_bank(
            "stopme", [_make_task("t1", td), _make_task("t2", td), _make_task("t3", td)]
        )
        self.sc = _make_scenario("bare")

    def _lock(self):
        from fathom.runlock import RunLock

        lock = RunLock("stopme", lock_root=self.lock_root, label="test run")
        lock.acquire(timeout_s=5.0, poll_s=0.02)
        self.addCleanup(lock.release)
        return lock

    def test_a_request_halts_the_matrix_at_the_next_boundary(self):
        from fathom.cli import EXIT_STOPPED
        from fathom.runlock import request_stop

        lock = self._lock()
        trials = {"n": 0}
        real_stop_requested = lock.stop_requested

        class _CountingExecutor(StubExecutor):
            def run_trial(self, task, workspace, scenario, runner):
                trials["n"] += 1
                if trials["n"] == 1:
                    request_stop("stopme", lock_root=self.outer.lock_root, reason="cap reached")
                return super().run_trial(task, workspace, scenario, runner)

        _CountingExecutor.outer = self
        code, out = _run_matrix(
            self.bank,
            [self.sc],
            repeats=1,
            ledger_dir=self.ledger_dir,
            run_lock=lock,
            executor_factory=lambda sc: _CountingExecutor(),
        )
        self.assertEqual(code, EXIT_STOPPED)
        self.assertIn("stop requested", out)
        self.assertIn("cap reached", out)
        self.assertEqual(trials["n"], 1, "the trial in flight finished; the next never started")
        # The ledger is intact and holds exactly the trial that completed.
        rows = [
            json.loads(line)
            for line in (self.ledger_dir / "stopme.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(sum(1 for r in rows if r.get("kind") == "trial"), 1)
        # The request is consumed, so a later run is not halted by a stale one.
        self.assertIsNone(real_stop_requested())

    def test_no_request_means_no_halt(self):
        """Also the halt's non-vacuity proof: the same bank runs all three trials.

        Without it, `trials == 1` above would be consistent with a loop that stops
        after one trial for any reason at all.
        """
        lock = self._lock()
        trials = {"n": 0}

        class _CountingExecutor(StubExecutor):
            def run_trial(self, task, workspace, scenario, runner):
                trials["n"] += 1
                return super().run_trial(task, workspace, scenario, runner)

        code, out = _run_matrix(
            self.bank,
            [self.sc],
            repeats=1,
            ledger_dir=self.ledger_dir,
            run_lock=lock,
            executor_factory=lambda sc: _CountingExecutor(),
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(trials["n"], 3)
        self.assertNotIn("stop requested", out)

    def test_stop_on_an_unheld_bank_is_not_an_error(self):
        import contextlib

        from fathom.cli import _cmd_stop

        args = types.SimpleNamespace(
            bank="nobody-holds-this",
            at_boundary=True,
            now=False,
            reason="",
            lock_root=str(self.lock_root),
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = _cmd_stop(args)
        self.assertEqual(code, EXIT_OK, "a stop that finds nothing to stop did its job")
        self.assertIn("nothing holds the lock", buf.getvalue())

    def test_stop_names_the_holder_and_records_the_reason(self):
        import contextlib

        from fathom.cli import _cmd_stop

        lock = self._lock()
        args = types.SimpleNamespace(
            bank="stopme",
            at_boundary=True,
            now=False,
            reason="program cap",
            lock_root=str(self.lock_root),
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = _cmd_stop(args)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("stop requested for bank 'stopme'", buf.getvalue())
        self.assertIn("pid", buf.getvalue())
        req = lock.stop_requested()
        self.assertIsNotNone(req)
        self.assertEqual(req.reason, "program cap")
        self.assertTrue(req.at_boundary, "at-boundary is the default: it loses nothing bought")


# ---------------------------------------------------------------------------
# A default FATHOM_STREAM_DIR for an arm with a [context] inject or a
# non-default tool allowance; an explicit value always wins; validate notes it.
# ---------------------------------------------------------------------------


class StreamDirDefaultTests(_Base):
    """Streams are the only record of what a treatment arm's agent actually did.

    Bare-control arms (default tools, no context inject) are unaffected — they
    are not the arms this row is about, and forcing a stream dir on every arm
    would silently start writing to disk for every existing bank.
    """

    def setUp(self):
        super().setUp()
        self._saved_stream_dir = __import__("os").environ.pop("FATHOM_STREAM_DIR", None)

    def tearDown(self):
        import os

        if self._saved_stream_dir is None:
            os.environ.pop("FATHOM_STREAM_DIR", None)
        else:
            os.environ["FATHOM_STREAM_DIR"] = self._saved_stream_dir
        super().tearDown()

    def _observed_stream_dirs(self, scenario) -> list[str | None]:
        import os

        seen: list[str | None] = []

        def _record(task, ws, sc):
            seen.append(os.environ.get("FATHOM_STREAM_DIR"))
            return _ok_result()

        _run_matrix(
            self.bank,
            [scenario],
            repeats=1,
            ledger_dir=self.ledger_dir,
            executor_factory=lambda sc: StubExecutor(result_fn=_record),
            # Arming verification is a different gate (FATH-B01), orthogonal to
            # the stream-directory default; skip it so a declared [context] inject
            # reaches the trial loop here without a probe.
            skip_arming_check=True,
        )
        return seen

    def test_context_inject_arm_gets_a_default_stream_dir_under_the_run_output(self):
        sc = _make_scenario(context=ContextConfig(inject="/some/skill-body.md"))
        seen = self._observed_stream_dirs(sc)
        self.assertTrue(seen, "the stub executor was never called")
        for value in seen:
            self.assertIsNotNone(value, "a [context]-inject arm must default a stream dir")
            self.assertIn(str(pathlib.Path(".fathom") / "streams" / self.bank.name), value)

    def test_non_default_tool_allowance_arm_gets_a_default_stream_dir(self):
        sc = _make_scenario(tools=ToolsConfig(source="none", allowed=("Read", "Bash")))
        seen = self._observed_stream_dirs(sc)
        for value in seen:
            self.assertIsNotNone(value, "a non-default-tools arm must default a stream dir")

    def test_bare_arm_without_either_gets_no_stream_dir(self):
        sc = _make_scenario()  # tools=ToolsConfig(source="none"), no allowed/disallowed, no context
        seen = self._observed_stream_dirs(sc)
        self.assertTrue(seen)
        for value in seen:
            self.assertIsNone(value, "a bare control arm must not get a default stream dir")

    def test_explicit_stream_dir_is_kept_even_for_a_bare_arm(self):
        import os

        os.environ["FATHOM_STREAM_DIR"] = "/an/explicit/dir"
        try:
            sc = _make_scenario()
            seen = self._observed_stream_dirs(sc)
        finally:
            os.environ.pop("FATHOM_STREAM_DIR", None)
        for value in seen:
            self.assertEqual(value, "/an/explicit/dir")

    def test_explicit_stream_dir_is_kept_for_a_context_inject_arm_too(self):
        import os

        os.environ["FATHOM_STREAM_DIR"] = "/an/explicit/dir"
        try:
            sc = _make_scenario(context=ContextConfig(inject="/some/skill-body.md"))
            seen = self._observed_stream_dirs(sc)
        finally:
            os.environ.pop("FATHOM_STREAM_DIR", None)
        for value in seen:
            self.assertEqual(value, "/an/explicit/dir", "an explicit value always wins")


class ValidateNotesStreamDirTests(unittest.TestCase):
    """`fathom validate` says where `fathom run` will keep a treatment arm's streams.

    It is a note, not a warning: `fathom run` sets the stream directory itself for
    exactly these arms, so the operator has nothing to do.
    """

    def setUp(self):
        import os

        self._tmp = tempfile.mkdtemp()
        self.scenarios_dir = Path(self._tmp) / "scenarios"
        self.scenarios_dir.mkdir()
        self._saved_stream_dir = os.environ.pop("FATHOM_STREAM_DIR", None)

    def tearDown(self):
        import os

        shutil.rmtree(self._tmp, ignore_errors=True)
        if self._saved_stream_dir is None:
            os.environ.pop("FATHOM_STREAM_DIR", None)
        else:
            os.environ["FATHOM_STREAM_DIR"] = self._saved_stream_dir

    def _write_scenario(self, name: str, extra: str = "") -> None:
        (self.scenarios_dir / f"{name}.toml").write_text(
            f"""\
name = "{name}"
adapter = "claude-cli"
model = "claude-opus-4-8"
strategy = "single-session"
effort = "high"

[tools]
source = "none"

{extra}
""",
            encoding="utf-8",
        )

    def test_notes_a_context_inject_arm_and_says_no_action_is_needed(self):
        import contextlib

        from fathom.cli import _note_stream_dir

        self._write_scenario("treated", extra='[context]\ninject = "skill-body.md"\n')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _note_stream_dir(self.scenarios_dir)
        self.assertIn("FATHOM_STREAM_DIR", buf.getvalue())
        self.assertIn("treated", buf.getvalue())
        self.assertIn("no action is needed", buf.getvalue())
        self.assertNotIn("WARNING", buf.getvalue())

    def test_says_nothing_when_only_bare_arms_are_planned(self):
        import contextlib

        from fathom.cli import _note_stream_dir

        self._write_scenario("bare")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _note_stream_dir(self.scenarios_dir)
        self.assertEqual(buf.getvalue(), "")

    def test_says_nothing_when_FATHOM_STREAM_DIR_is_already_set(self):
        import contextlib
        import os

        from fathom.cli import _note_stream_dir

        self._write_scenario("treated", extra='[context]\ninject = "skill-body.md"\n')
        os.environ["FATHOM_STREAM_DIR"] = "/already/set"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _note_stream_dir(self.scenarios_dir)
        self.assertEqual(buf.getvalue(), "")


# ---------------------------------------------------------------------------
# The entry point: --version, and where a command writes
# ---------------------------------------------------------------------------


def _call_main(argv: list[str]) -> tuple[int, str, str]:
    """``fathom.cli.main(argv)`` with its exit code, stdout and stderr.

    argparse ends ``--version`` and ``--help`` with SystemExit; that is folded into the
    returned code so every test reads the same shape.
    """
    import contextlib

    from fathom.cli import main

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class VersionFlagTests(unittest.TestCase):
    """`fathom --version` reports the installed distribution, not a copy of the number."""

    def test_it_prints_the_installed_version_and_exits_zero(self):
        from importlib import metadata

        try:
            installed = metadata.version("fathom")
        except metadata.PackageNotFoundError:
            self.skipTest("fathom is not installed here; the flag reads installed metadata")
        code, out, _ = _call_main(["--version"])
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.strip(), f"fathom {installed}")

    def test_it_says_so_when_there_is_no_installed_distribution(self):
        from importlib import metadata
        from unittest import mock

        def _absent(name):
            raise metadata.PackageNotFoundError(name)

        with mock.patch("importlib.metadata.version", _absent):
            code, out, _ = _call_main(["--version"])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("fathom unknown", out)
        self.assertIn("not installed", out)


class UnpublishedWarningTests(unittest.TestCase):
    """`fathom report` warns when no write-up names the bank.

    docs/reports/LEDGER-INDEX.md is generated and names every bank with a ledger, so it
    cannot count as a write-up: while it did, the warning could never fire in a data root.
    """

    BANK = "example-v1"

    def _warning(self, files: dict[str, str]) -> str:
        import contextlib

        from fathom.cli import _warn_if_unpublished

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, text in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            err = io.StringIO()
            with contextlib.chdir(root), contextlib.redirect_stderr(err):
                _warn_if_unpublished(self.BANK)
        return err.getvalue()

    def _index(self) -> dict[str, str]:
        return {
            "docs/reports/LEDGER-INDEX.md": (
                f"| Bank | ledger sha256 |\n|---|---|\n| `{self.BANK}` | `0123abcd` |\n"
            )
        }

    def test_the_ledger_index_alone_does_not_count_as_a_write_up(self):
        warning = self._warning(self._index())
        self.assertIn("WARNING", warning)
        self.assertIn(self.BANK, warning)

    def test_a_report_that_names_the_bank_silences_it(self):
        files = self._index()
        files["docs/reports/2026-01-01-findings.md"] = f"# Findings on {self.BANK}\n"
        self.assertEqual(self._warning(files), "")

    def test_a_report_named_after_the_bank_silences_it(self):
        files = self._index()
        files[f"docs/reports/2026-01-01-{self.BANK}.md"] = "# Findings\n"
        self.assertEqual(self._warning(files), "")

    def test_a_status_row_silences_it(self):
        files = self._index()
        files["docs/STATUS.md"] = f"| {self.BANK} | done |\n"
        self.assertEqual(self._warning(files), "")


class DataRootWarningTests(unittest.TestCase):
    """An unmarked working directory that holds tasks/ or ledger/ is used, with a warning.

    It is the last step of finding a data root (fathom.home): nothing was named with
    --home or FATHOM_HOME, and no marked directory is at or above it. Every data command
    warns once; `run` (when it spends) and `void` also name the ledger they append to. The
    warning neither refuses nor changes an exit code. A fathom.toml that cannot be read is
    different: it may be meant as the marker, so finding the data root stops there with
    an error, and nothing is appended.
    """

    MARK = "not a fathom data root"

    # `--limit 0` plans nothing, so the run ends at "nothing to do" and never reaches a
    # gate or a spawn; --skip-credential-check and --no-lock keep it off this seat's state.
    RUN = ("run", "b", "--repeats", "1", "--limit", "0", "--skip-credential-check", "--no-lock")
    VOID = ("void", "b", "--scenario", "arm", "--repeat", "0", "--reason", "defect")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        bank_dir = self.root / "tasks" / "b"
        (bank_dir / "t1").mkdir(parents=True)
        (bank_dir / "bank.toml").write_text(
            'name = "b"\ndataset_version = "1"\nholdout = []\n', encoding="utf-8"
        )
        (bank_dir / "t1" / "task.toml").write_text(
            'id = "t1"\ninstruction = "x"\n[limits]\ntrial_timeout_s = 1\n'
            '[verify]\nentry = "verify.py"\n',
            encoding="utf-8",
        )
        (bank_dir / "t1" / "verify.py").write_text("print('{}')", encoding="utf-8")
        (self.root / "scenarios").mkdir()
        (self.root / "scenarios" / "arm.toml").write_text(
            'name = "arm"\nadapter = "claude-cli"\nmodel = "m"\n'
            'strategy = "single-session"\neffort = "high"\n'
            '[tools]\nsource = "none"\nallowed = ["Read"]\n',
            encoding="utf-8",
        )
        (self.root / "ledger").mkdir()
        trial = {
            "kind": "trial",
            "bank": "b",
            "task_id": "t1",
            "repeat": 0,
            "status": "completed",
            "dataset_version": "1",
            "config_hash": "h" * 64,
            "tool_git_sha": "",
            "cli_version": "",
            "pin_level": PIN_STRONG,
            "scenario": "arm",
        }
        (self.root / "ledger" / "b.jsonl").write_text(json.dumps(trial) + "\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _mark(self, text: str = "[data_root]\nschema = 1\n") -> None:
        (self.root / "fathom.toml").write_text(text, encoding="utf-8")

    def _main(self, argv: Sequence[str]) -> tuple[int, str, str]:
        """Run ``main`` from the temporary root: (exit code, stderr, the ledger path)."""
        import contextlib

        with contextlib.chdir(self.root):
            ledger = Path.cwd() / "ledger" / "b.jsonl"
            code, _, err = _call_main(list(argv))
        return code, err, str(ledger)

    def test_a_run_outside_a_data_root_warns_once_and_names_the_ledger(self):
        code, err, ledger = self._main(self.RUN)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err.count(self.MARK), 1, err)
        self.assertIn(ledger, err)
        self.assertIn("[data_root]", err)
        self.assertIn("schema = 1", err)

    def test_a_run_inside_a_data_root_says_nothing_and_exits_the_same(self):
        outside, _, _ = self._main(self.RUN)
        self._mark()
        inside, err, _ = self._main(self.RUN)
        self.assertEqual(inside, outside)
        self.assertNotIn(self.MARK, err)

    def test_a_fathom_toml_without_the_marker_table_still_warns(self):
        self._mark('[[reconcile.known]]\ncheck = "x"\nsubject = "y"\nkey = "z"\nreason = "r"\n')
        _, err, _ = self._main(self.RUN)
        self.assertEqual(err.count(self.MARK), 1, err)
        self.assertIn("has no [data_root] table", err)
        self.assertNotIn("create fathom.toml", err)

    def _rows(self) -> int:
        return len((self.root / "ledger" / "b.jsonl").read_text(encoding="utf-8").splitlines())

    def test_an_unreadable_fathom_toml_stops_the_command_and_is_named(self):
        """A UTF-16 file (what Windows PowerShell 5.1 writes with `>`) is there already.

        The error says why it cannot be read, as reconcile and the index check do, does not
        tell the user to create a file they have, and nothing is appended.
        """
        (self.root / "fathom.toml").write_bytes("[data_root]\nschema = 1\n".encode("utf-16"))
        before = self._rows()
        for argv in (self.RUN, self.VOID):
            with self.subTest(command=argv[0]):
                code, err, _ = self._main(argv)
                self.assertEqual(code, 1, err)
                self.assertIn("UTF-16", err)
                self.assertIn("save the file again as UTF-8", err)
                self.assertNotIn(self.MARK, err)
                self.assertNotIn("create fathom.toml", err)
                self.assertEqual(self._rows(), before, "nothing may be appended")

    def test_the_warning_and_reconcile_agree_on_what_a_data_root_is(self):
        import codecs

        from fathom import home
        from fathom.ledgerindex import is_data_root

        def _marked(root: Path) -> bool:
            try:
                return home.resolve(None, env={}, cwd=root).marked
            except home.DataRootError:
                return False

        marker = b"[data_root]\nschema = 1\n"
        cases = {
            "no file": None,
            "marker": marker,
            "marker after a UTF-8 byte-order mark": codecs.BOM_UTF8 + marker,
            "no table": b"[reconcile]\n",
            "a key, not a table": b"data_root = 1\n",
            "UTF-16": marker.decode("ascii").encode("utf-16"),
            "not TOML": b"[data_root\n",
        }
        for label, content in cases.items():
            with self.subTest(case=label):
                path = self.root / "fathom.toml"
                path.unlink(missing_ok=True)
                if content is not None:
                    path.write_bytes(content)
                self.assertEqual(_marked(self.root), is_data_root(self.root))

    def test_a_fathom_toml_that_is_not_toml_is_named(self):
        self._mark("[data_root\nschema = 1\n")
        code, err, _ = self._main(self.RUN)
        self.assertEqual(code, 1, err)
        self.assertIn("not valid TOML", err)
        self.assertNotIn(self.MARK, err)
        self.assertNotIn("create fathom.toml", err)

    def test_a_dry_run_warns_once_without_naming_a_ledger(self):
        """A dry run appends nothing, but it still runs against the unmarked directory."""
        code, err, ledger = self._main(("run", "b", "--repeats", "1", "--dry-run"))
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err.count(self.MARK), 1, err)
        self.assertNotIn("appends to", err)
        self.assertNotIn(ledger, err)

    def test_a_void_outside_a_data_root_warns_once_and_still_appends(self):
        code, err, ledger = self._main(self.VOID)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err.count(self.MARK), 1, err)
        self.assertIn(ledger, err)
        rows = (self.root / "ledger" / "b.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(rows[-1])["kind"], "void")

    def test_a_void_inside_a_data_root_says_nothing(self):
        self._mark()
        code, err, _ = self._main(self.VOID)
        self.assertEqual(code, EXIT_OK)
        self.assertNotIn(self.MARK, err)

    def test_a_void_that_finds_no_trial_keeps_its_exit_code(self):
        void = ("void", "b", "--scenario", "absent", "--repeat", "0", "--reason", "defect")
        outside, err_outside, _ = self._main(void)
        self._mark()
        inside, _, _ = self._main(void)
        self.assertEqual(outside, 1)
        self.assertEqual(inside, outside)
        self.assertEqual(err_outside.count(self.MARK), 1, err_outside)


class ReportWithoutALedgerTests(unittest.TestCase):
    """`fathom report <bank>` fails when there is no ledger/<bank>.jsonl to render.

    Rendering one would write a scorecard holding only its heading and exit 0. Run where
    no data root resolves, it says so and how to make or name one; run in a data root
    without that ledger, it names the path it looked for. Either way it writes nothing.
    """

    BANK = "example-v1"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _report(self) -> tuple[int, str, str, str]:
        """(exit code, stdout, stderr, the ledger path the command should have looked for)."""
        import contextlib

        with contextlib.chdir(self.root):
            ledger = str(Path.cwd() / "ledger" / f"{self.BANK}.jsonl")
            code, out, err = _call_main(["report", self.BANK])
        return code, out, err, ledger

    def test_outside_a_data_root_it_fails_says_how_to_make_one_and_writes_nothing(self):
        code, out, err, _ = self._report()
        self.assertEqual(code, 1, out + err)
        self.assertIn("no fathom data root found", err)
        self.assertIn("[data_root]", err)
        self.assertIn("fathom init", err)
        self.assertIn("FATHOM_HOME", err)
        self.assertNotIn("report written", out)
        self.assertFalse((self.root / "report").exists())

    def test_inside_a_data_root_it_fails_without_calling_the_root_wrong(self):
        (self.root / "fathom.toml").write_text("[data_root]\nschema = 1\n", encoding="utf-8")
        (self.root / "ledger").mkdir()
        code, out, err, ledger = self._report()
        self.assertEqual(code, 1, out + err)
        self.assertIn(ledger, err)
        self.assertNotIn("not a fathom data root", err)
        self.assertFalse((self.root / "report").exists())

    def test_a_ledger_that_exists_still_renders(self):
        (self.root / "fathom.toml").write_text("[data_root]\nschema = 1\n", encoding="utf-8")
        (self.root / "ledger").mkdir()
        (self.root / "ledger" / f"{self.BANK}.jsonl").write_text("", encoding="utf-8")
        code, out, err, _ = self._report()
        self.assertEqual(code, EXIT_OK, out + err)
        self.assertIn("report written", out)
        self.assertTrue((self.root / "report" / f"scorecard-{self.BANK}.md").is_file())


class ReportDatasetVersionTests(unittest.TestCase):
    """`fathom report <bank>` options on a two-version ledger: --dataset-version, --per-trial."""

    BANK = "example-v1"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "fathom.toml").write_text("[data_root]\nschema = 1\n", encoding="utf-8")
        (self.root / "ledger").mkdir()
        rows = [
            {
                "kind": "trial",
                "bank": self.BANK,
                "task_id": "add",
                "repeat": 0,
                "status": "completed",
                "dataset_version": dv,
                "config_hash": "aaa",
                "verifier_results": {"c": True},
                "scenario": "bare",
                "holdout": False,
                "infra_error": False,
            }
            for dv in ("v1", "v2")
        ]
        text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
        (self.root / "ledger" / f"{self.BANK}.jsonl").write_text(text, encoding="utf-8")

    def _report(self, *extra: str) -> tuple[int, str, str]:
        import contextlib

        with contextlib.chdir(self.root):
            return _call_main(["report", self.BANK, *extra])

    def test_a_chosen_version_is_written_to_its_own_file_and_named(self):
        code, out, err = self._report("--dataset-version", "v1")
        self.assertEqual(code, EXIT_OK, out + err)
        name = f"scorecard-{self.BANK}--v1.md"
        self.assertIn(name, out)
        self.assertTrue((self.root / "report" / name).is_file())
        self.assertFalse((self.root / "report" / f"scorecard-{self.BANK}.md").exists())

    def test_the_default_writes_the_current_scorecard_only(self):
        code, out, err = self._report()
        self.assertEqual(code, EXIT_OK, out + err)
        self.assertTrue((self.root / "report" / f"scorecard-{self.BANK}.md").is_file())
        self.assertEqual(len(list((self.root / "report").glob("*.md"))), 1)

    def test_an_unknown_version_exits_1_and_names_the_versions_held(self):
        code, out, err = self._report("--dataset-version", "v9")
        self.assertEqual(code, 1, out + err)
        self.assertIn("v9", err)
        self.assertIn("v1", err)
        self.assertIn("v2", err)
        self.assertNotIn("report written", out)

    # --per-trial
    HEADER = "| Arm | Task | Repeat | Status | Runs | Est. USD |"

    def test_per_trial_prints_the_table_header(self):
        code, out, err = self._report("--per-trial")
        self.assertEqual(code, EXIT_OK, out + err)
        self.assertIn(self.HEADER, out)
        self.assertIn("| bare | add | 0 | completed | 0 |", out)

    def test_without_the_flag_no_table_is_printed(self):
        code, out, err = self._report()
        self.assertEqual(code, EXIT_OK, out + err)
        self.assertNotIn(self.HEADER, out)

    def test_the_scorecard_bytes_are_the_same_with_and_without_the_flag(self):
        scorecard = self.root / "report" / f"scorecard-{self.BANK}.md"
        self._report()
        plain = scorecard.read_bytes()
        scorecard.unlink()
        code, out, err = self._report("--per-trial")
        self.assertEqual(code, EXIT_OK, out + err)
        self.assertEqual(scorecard.read_bytes(), plain)

    def test_it_combines_with_a_chosen_dataset_version(self):
        code, out, err = self._report("--per-trial", "--dataset-version", "v1")
        self.assertEqual(code, EXIT_OK, out + err)
        self.assertIn(self.HEADER, out)
        self.assertTrue((self.root / "report" / f"scorecard-{self.BANK}--v1.md").is_file())


class ReportMcpCallsTests(unittest.TestCase):
    """`fathom report` counts a mounted plugin's MCP calls from the streams `fathom run` kept.

    The command runs from the data root, so the default stream directory is the data root's
    `.fathom/streams/<bank>/` whatever directory it starts in, and a relative
    FATHOM_STREAM_DIR is taken from the directory it starts in, as `fathom run` takes it.
    """

    BANK = "example-v1"
    STREAM = (
        '{"type": "system", "subtype": "init", "mcp_servers": [{"name": "srv"}]}\n'
        '{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "u1",'
        ' "name": "mcp__srv__x", "input": {}}]}}\n'
        '{"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "u1",'
        ' "content": "ok"}]}}\n'
        '{"type": "result", "subtype": "success"}\n'
    )
    ROW = "| nudge | 1/1 | 1/1/1 |  |"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        saved = os.environ.pop("FATHOM_STREAM_DIR", None)
        self.addCleanup(
            lambda: (
                os.environ.__setitem__("FATHOM_STREAM_DIR", saved)
                if saved is not None
                else os.environ.pop("FATHOM_STREAM_DIR", None)
            )
        )
        self.root = Path(self._tmp.name)
        (self.root / "fathom.toml").write_text("[data_root]\nschema = 1\n", encoding="utf-8")
        (self.root / "ledger").mkdir()
        (self.root / "sub").mkdir()
        row = {
            "kind": "trial",
            "bank": self.BANK,
            "task_id": "add",
            "repeat": 0,
            "status": "completed",
            "dataset_version": "v1",
            "config_hash": "aaa",
            "config_preimage": json.dumps({"plugins": [{"name": "example"}]}),
            "verifier_results": {"c": True},
            "scenario": "nudge",
            "holdout": False,
            "infra_error": False,
        }
        ledger = self.root / "ledger" / f"{self.BANK}.jsonl"
        ledger.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    def _keep(self, directory: Path) -> None:
        directory.mkdir(parents=True)
        name = f"{self.BANK}--nudge--add--r0--a1--1700000000000.ndjson"
        (directory / name).write_text(self.STREAM, encoding="utf-8")

    def _scorecard(self) -> str:
        import contextlib

        with contextlib.chdir(self.root / "sub"):
            code, out, err = _call_main(["report", self.BANK])
        self.assertEqual(code, EXIT_OK, out + err)
        return (self.root / "report" / f"scorecard-{self.BANK}.md").read_text(encoding="utf-8")

    def test_the_data_roots_kept_streams_are_read_from_a_subdirectory(self):
        self._keep(self.root / ".fathom" / "streams" / self.BANK)
        self.assertIn(self.ROW, self._scorecard())

    def test_a_relative_fathom_stream_dir_is_taken_from_the_starting_directory(self):
        self._keep(self.root / "sub" / "kept")
        os.environ["FATHOM_STREAM_DIR"] = "kept"
        self.assertIn(self.ROW, self._scorecard())

    def test_without_kept_streams_the_arm_says_so(self):
        self.assertIn("| nudge | 0/1 | no streams kept |  |", self._scorecard())


class ReconcileRefusesANonRootFirstTests(unittest.TestCase):
    """`fathom reconcile` refuses a directory that is no root before any check reads it.

    The checks read every ledger under ledger/ and walk scenarios/. Run first, an
    undecodable ledger in a directory about to be refused ended in a traceback and exit 1
    instead of the documented refusal (exit 13, one error line).
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _reconcile(self, *extra: str) -> tuple[int, str, str]:
        import contextlib

        with contextlib.chdir(self.root):
            return _call_main(["reconcile", *extra])

    def test_a_non_root_holding_an_undecodable_ledger_is_refused(self):
        (self.root / "ledger").mkdir()
        (self.root / "ledger" / "x.jsonl").write_bytes(b'{"kind": "trial"}\n\xff\xfe\n')
        code, out, err = self._reconcile()
        self.assertEqual(code, 13, out + err)
        self.assertIn("neither a fathom data root", err)
        self.assertEqual(len(err.strip().splitlines()), 1, err)
        self.assertNotIn("reconciling", out)

    def test_no_check_runs_in_a_non_root(self):
        from unittest import mock

        from fathom import reconcile as _reconcile

        with mock.patch.object(_reconcile, "_execute") as execute:
            code, _, err = self._reconcile()
        self.assertEqual(code, 13, err)
        execute.assert_not_called()

    def test_an_unreadable_fathom_toml_is_named_before_the_refusal(self):
        (self.root / "fathom.toml").write_bytes("[data_root]\nschema = 1\n".encode("utf-16"))
        code, _, err = self._reconcile()
        self.assertEqual(code, 13, err)
        self.assertIn("must be UTF-8", err)
        self.assertNotIn("neither a fathom data root", err)

    def test_an_unknown_check_is_named_wherever_it_runs(self):
        code, _, err = self._reconcile("--check", "no-such-check")
        self.assertEqual(code, 13, err)
        self.assertIn("no-such-check", err)


class InitNextStepsTests(unittest.TestCase):
    """The steps `fathom init` prints must work on the root it has just made."""

    def test_the_smoke_step_leaves_out_the_engine_boundary_check(self):
        # A fresh root has no scenarios/series.toml, and the engine-boundary check fails
        # without one, after the other checks have already spent.
        from fathom.cli import _init_next_steps

        steps = _init_next_steps()
        self.assertIn("fathom smoke --no-engine-boundary", steps)
        self.assertIn("scenarios/series.toml", steps)


class TrialRunnerStagesArmFilesTests(unittest.TestCase):
    """The runner `fathom run` builds passes copies of the arm's files in the argv.

    tests/test_spawn_env.py checks that no argv element then names the data root.
    """

    def test_the_default_runner_stages(self):
        from fathom.cli import _default_runner_factory

        runner = _default_runner_factory(
            _make_scenario(tools=ToolsConfig(source="none", allowed=("Read",)))
        )
        self.assertTrue(runner.stage_files)


class DataRootWithheldFromChildrenTests(unittest.TestCase):
    """While a command runs against a data root, no child is handed a value naming it.

    `uv run fathom` from a data repository that pins fathom puts VIRTUAL_ENV and a PATH
    entry inside the data root; the strip by name misses both.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "root"
        self.root.mkdir()
        self.tasks_elsewhere = Path(self._tmp.name) / "tasks-elsewhere"
        self.tasks_elsewhere.mkdir()

    def _args(self, **kw):
        return types.SimpleNamespace(
            command="report", tasks_dir=None, scenarios_dir=None, ledger_dir=None, **kw
        )

    def test_the_data_root_is_registered_for_the_command_only(self):
        from unittest import mock

        import fathom.home as _home
        from fathom.adapters.claude_cli import hidden_dirs, make_spawn_env
        from fathom.cli import _running_in

        venv = self.root / ".venv"
        args = self._args()
        args.tasks_dir = str(self.tasks_elsewhere)
        with mock.patch.dict(
            os.environ,
            {"VIRTUAL_ENV": str(venv), "EXAMPLE_TASKS": str(self.tasks_elsewhere / "b")},
        ):
            with _running_in(_home.DataRoot(path=self.root, origin="--home"), args):
                registered = {os.path.normcase(str(p)) for p in hidden_dirs()}
                env = make_spawn_env("cfg")
            after = hidden_dirs()
            env_after = make_spawn_env("cfg")
        self.assertIn(os.path.normcase(str(self.root)), registered)
        self.assertIn(os.path.normcase(str(self.tasks_elsewhere)), registered)
        self.assertNotIn("VIRTUAL_ENV", env)
        self.assertNotIn("EXAMPLE_TASKS", env)
        self.assertEqual(after, ())
        self.assertIn("VIRTUAL_ENV", env_after)


# ---------------------------------------------------------------------------
# Per-trial progress line and closing run summary
# ---------------------------------------------------------------------------


class _FlushCountingStream(io.StringIO):
    """A stream that records where in its text each flush() happened."""

    def __init__(self) -> None:
        super().__init__()
        self.flush_offsets: list[int] = []

    def flush(self) -> None:
        self.flush_offsets.append(len(self.getvalue()))
        super().flush()

    def flushed_lines(self, prefix: str) -> list[tuple[str, bool]]:
        """Each line starting with *prefix*, and whether a flush came right after it."""
        found: list[tuple[str, bool]] = []
        offset = 0
        for line in self.getvalue().splitlines(keepends=True):
            offset += len(line)
            if line.startswith(prefix):
                found.append((line.rstrip("\n"), offset in self.flush_offsets))
        return found


def _ledger_trials(ledger_dir: pathlib.Path, bank: str) -> list[dict]:
    path = ledger_dir / f"{bank}.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return [r for r in rows if r.get("kind") == "trial"]


def _summary_fields(text: str) -> dict:
    """Parse the one `run summary:` line of *text* into its counts."""
    import re

    lines = [ln for ln in text.splitlines() if ln.startswith("run summary:")]
    assert len(lines) == 1, f"expected exactly one run summary line, got {lines}"
    line = lines[0]
    m = re.fullmatch(
        r"run summary: ledger (?P<ledger>.+?); completed (?P<c>\d+), errored (?P<e>\d+) "
        r"this invocation; (?:blocked (?P<b>\d+) \(comparator incomplete\); )?"
        r"skipped (?P<s>\d+) \(already done\); not started (?P<u>\d+); "
        r"spent \$(?P<usd>\d+\.\d\d) this invocation; resume: (?P<resume>.+)",
        line,
    )
    assert m is not None, f"unexpected summary shape: {line}"
    return {
        "ledger": m["ledger"],
        "completed": int(m["c"]),
        "errored": int(m["e"]),
        # Present only when the run's arms declare a comparator.
        "blocked": int(m["b"]) if m["b"] is not None else None,
        "skipped": int(m["s"]),
        "not_started": int(m["u"]),
        "usd": float(m["usd"]),
        "resume": m["resume"],
    }


class TestProgressAndSummary(_Base):
    """One flushed line per trial, and a closing summary on every exit after the loop began."""

    def _counts(self) -> tuple[int, int]:
        """(completed, errored) trial rows in the ledger file, counted by reading it."""
        trials = _ledger_trials(self.ledger_dir, "test-bank")
        return (
            sum(1 for t in trials if t["status"] == "completed"),
            sum(1 for t in trials if t["status"] == "errored"),
        )

    def test_one_flushed_progress_line_per_planned_trial(self):
        out = _FlushCountingStream()
        code, _ = _run_matrix(
            self.bank, self.scenarios, repeats=2, ledger_dir=self.ledger_dir, out=out
        )
        self.assertEqual(code, EXIT_OK)
        lines = out.flushed_lines("trial done:")
        self.assertEqual(len(lines), 2 * 2 * 2, "arms x tasks x repeats")
        for text, flushed in lines:
            self.assertTrue(flushed, f"not flushed right after it was written: {text}")
        self.assertEqual(lines[0][0], "trial done: 1/8 bare/task-1 r0 completed [$0.05]")
        self.assertEqual(lines[-1][0], "trial done: 8/8 single-long/task-2 r1 completed [$0.40]")

    def test_the_summary_counts_equal_the_rows_appended(self):
        def verifier(entry, ws, timeout_s=60):
            # the second trial's verifier crashes: an errored row, not a completed one
            verifier.n += 1
            if verifier.n == 2:
                return VerifierResult(
                    outcome="error", criteria=None, stdout="", stderr="boom", exit_code=1
                )
            return _stub_verifier(entry, ws, timeout_s)

        verifier.n = 0
        out = _FlushCountingStream()
        code, _ = _run_matrix(
            self.bank,
            self.scenarios,
            repeats=1,
            ledger_dir=self.ledger_dir,
            out=out,
            verifier_fn=verifier,
        )
        self.assertEqual(code, EXIT_OK)
        fields = _summary_fields(out.getvalue())
        completed, errored = self._counts()
        self.assertEqual((fields["completed"], fields["errored"]), (completed, errored))
        self.assertEqual((completed, errored), (3, 1))
        self.assertEqual(fields["skipped"], 0)
        self.assertEqual(fields["not_started"], 0)
        self.assertAlmostEqual(fields["usd"], 0.20)
        self.assertEqual(fields["ledger"], str((self.ledger_dir / "test-bank.jsonl").resolve()))
        self.assertTrue(pathlib.Path(fields["ledger"]).is_absolute())
        self.assertEqual(fields["resume"], "fathom run test-bank --repeats 1")
        flushed = out.flushed_lines("run summary:")
        self.assertEqual(len(flushed), 1)
        self.assertTrue(flushed[0][1], "the summary is flushed")

    def test_skipped_counts_what_an_earlier_invocation_finished(self):
        _run_matrix(self.bank, [self.sc_a], repeats=1, ledger_dir=self.ledger_dir)
        out = io.StringIO()
        _run_matrix(self.bank, [self.sc_a], repeats=2, ledger_dir=self.ledger_dir, out=out)
        fields = _summary_fields(out.getvalue())
        self.assertEqual(fields["skipped"], 2)
        self.assertEqual(fields["completed"], 2)
        self.assertEqual(len(_ledger_trials(self.ledger_dir, "test-bank")), 4)

    def test_a_resume_command_passed_in_is_printed_as_given(self):
        out = io.StringIO()
        _run_matrix(
            self.bank,
            [self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
            out=out,
            resume_cmd="fathom run test-bank --repeats 1 --tasks task-1",
        )
        self.assertEqual(
            _summary_fields(out.getvalue())["resume"],
            "fathom run test-bank --repeats 1 --tasks task-1",
        )

    def test_an_infrastructure_stop_prints_the_summary(self):
        calls = {"n": 0}

        def result(task, ws, sc):
            calls["n"] += 1
            return _infra_result() if calls["n"] == 3 else _ok_result()

        out = _FlushCountingStream()
        code, _ = _run_matrix(
            self.bank,
            self.scenarios,
            repeats=1,
            ledger_dir=self.ledger_dir,
            out=out,
            executor_factory=lambda sc: StubExecutor(result_fn=result),
        )
        self.assertEqual(code, EXIT_INFRASTRUCTURE)
        fields = _summary_fields(out.getvalue())
        self.assertEqual(self._counts(), (2, 0))
        self.assertEqual((fields["completed"], fields["errored"]), (2, 0))
        # The stopped trial has no ledger row, so a resume runs it: it is not "done".
        self.assertEqual(fields["not_started"], 2)
        self.assertAlmostEqual(fields["usd"], 0.10)
        lines = out.flushed_lines("trial done:")
        self.assertEqual(len(lines), 3)
        self.assertIn("3/4 single-long/task-1 r0 infrastructure", lines[2][0])
        self.assertTrue(all(flushed for _, flushed in lines))

    def test_a_fixture_drift_stop_prints_the_summary(self):
        root = Path(self._tmp) / "fx"
        (root / "fixtures" / "pkg").mkdir(parents=True)
        (root / "fixtures" / "pkg" / "a.py").write_text("print(1)\n", encoding="utf-8")
        task = Task(
            id="fx", instruction="x", limits={}, verify={"entry": "verify.py"}, task_dir=root
        )
        bank = _make_bank("test-bank", [task])
        out = io.StringIO()
        code, _ = _run_matrix(
            bank,
            [self.sc_a],
            repeats=2,
            ledger_dir=self.ledger_dir,
            out=out,
            stage_task_fn=_mutating_stage_factory(task, when="during"),
        )
        self.assertEqual(code, EXIT_INFRASTRUCTURE)
        fields = _summary_fields(out.getvalue())
        self.assertEqual(self._counts(), (0, 1))
        self.assertEqual((fields["completed"], fields["errored"]), (0, 1))
        self.assertEqual(fields["not_started"], 1)
        self.assertEqual(out.getvalue().count("trial done:"), 1)

    def test_the_run_budget_halt_prints_the_summary(self):
        from fathom.cli import EXIT_RUN_BUDGET

        out = _FlushCountingStream()
        code, _ = _run_matrix(
            self.bank,
            self.scenarios,
            repeats=1,
            ledger_dir=self.ledger_dir,
            out=out,
            max_run_usd=0.10,
        )
        self.assertEqual(code, EXIT_RUN_BUDGET)
        fields = _summary_fields(out.getvalue())
        self.assertEqual(self._counts(), (2, 0))
        self.assertEqual((fields["completed"], fields["errored"]), (2, 0))
        self.assertEqual(fields["not_started"], 2)
        self.assertEqual(len(out.flushed_lines("trial done:")), 2, "a halt starts no trial")

    def test_a_stop_request_prints_the_summary(self):
        from fathom.cli import EXIT_STOPPED

        class _Lock:
            def __init__(self) -> None:
                self.polls = 0

            def stop_requested(self):
                self.polls += 1
                return None if self.polls <= 1 else types.SimpleNamespace(reason="")

            def clear_stop_request(self):
                pass

        out = io.StringIO()
        code, _ = _run_matrix(
            self.bank,
            self.scenarios,
            repeats=1,
            ledger_dir=self.ledger_dir,
            out=out,
            run_lock=_Lock(),
        )
        self.assertEqual(code, EXIT_STOPPED)
        fields = _summary_fields(out.getvalue())
        self.assertEqual(self._counts(), (1, 0))
        self.assertEqual((fields["completed"], fields["errored"]), (1, 0))
        self.assertEqual(fields["not_started"], 3)

    def test_a_dry_run_and_an_empty_plan_print_neither_line(self):
        code, dry = _run_matrix(self.bank, self.scenarios, ledger_dir=self.ledger_dir, dry_run=True)
        self.assertEqual(code, EXIT_OK)
        self.assertNotIn("trial done", dry)
        self.assertNotIn("run summary", dry)
        _run_matrix(self.bank, self.scenarios, repeats=1, ledger_dir=self.ledger_dir)
        code, again = _run_matrix(self.bank, self.scenarios, repeats=1, ledger_dir=self.ledger_dir)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("nothing to do", again)
        self.assertNotIn("trial done", again)
        self.assertNotIn("run summary", again)


class TestResumeCommand(unittest.TestCase):
    """_resume_command rebuilds the invocation from parsed args, flags given only."""

    def _args(self, **kw):
        args = types.SimpleNamespace(
            bank="b",
            repeats=3,
            tasks_dir=None,
            scenarios_dir=None,
            ledger_dir=None,
            tasks=None,
            include_holdout=False,
            max_spawn_usd=None,
            max_run_usd=None,
            data_root=None,
            home=None,
        )
        for k, v in kw.items():
            setattr(args, k, v)
        return args

    def test_the_default_is_bank_and_repeats(self):
        from fathom.cli import _resume_command

        self.assertEqual(_resume_command(self._args(), spawn_cap=None), "fathom run b --repeats 3")

    def test_every_flag_given_is_carried_and_nothing_else(self):
        from fathom.cli import _resume_command

        args = self._args(
            scenarios_dir=Path("/x/arms"),
            tasks_dir=Path("/x/banks"),
            ledger_dir=Path("/x/led"),
            tasks="t1,t2",
            include_holdout=True,
            max_run_usd=12.5,
        )
        cmd = _resume_command(args, spawn_cap=2.0)
        self.assertEqual(
            cmd,
            "fathom run b --repeats 3 --tasks-dir "
            f"{Path('/x/banks')} --scenarios-dir {Path('/x/arms')} --ledger-dir {Path('/x/led')} "
            "--tasks t1,t2 --include-holdout --max-spawn-usd 2 --max-run-usd 12.5",
        )

    def test_a_path_that_is_the_data_roots_own_default_is_not_a_given_flag(self):
        from fathom.cli import _resume_command

        root = Path("/data")
        args = self._args(
            data_root=root,
            tasks_dir=root / "tasks",
            scenarios_dir=root / "scenarios",
            ledger_dir=root / "ledger",
        )
        self.assertEqual(_resume_command(args, spawn_cap=None), "fathom run b --repeats 3")

    def test_a_home_flag_that_was_given_leads_the_command(self):
        from fathom.cli import _resume_command

        args = self._args(home="rel/root", data_root=Path("/data"))
        self.assertEqual(
            _resume_command(args, spawn_cap=None),
            f"fathom --home {Path('/data')} run b --repeats 3",
        )

    def test_a_path_with_spaces_is_double_quoted(self):
        from fathom.cli import _resume_command

        args = self._args(ledger_dir=Path("/my data/led"))
        self.assertIn(
            f'--ledger-dir "{Path("/my data/led")}"', _resume_command(args, spawn_cap=None)
        )

    def _cmd_run_kwargs(self, **extra) -> dict:
        """The keyword arguments ``_cmd_run`` hands to ``run_matrix`` for a one-arm bank."""
        from unittest import mock

        from fathom.cli import _cmd_run

        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            bank_dir = tmp_p / "tasks" / "b"
            (bank_dir / "t1").mkdir(parents=True)
            (bank_dir / "bank.toml").write_text(
                'name = "b"\ndataset_version = "1"\nholdout = []\n', encoding="utf-8"
            )
            (bank_dir / "t1" / "task.toml").write_text(
                'id = "t1"\ninstruction = "x"\n[limits]\ntrial_timeout_s = 1\n'
                '[verify]\nentry = "verify.py"\n',
                encoding="utf-8",
            )
            (bank_dir / "t1" / "verify.py").write_text("print('{}')", encoding="utf-8")
            (tmp_p / "scenarios").mkdir()
            (tmp_p / "scenarios" / "arm.toml").write_text(
                'name = "arm"\nadapter = "claude-cli"\nmodel = "m"\n'
                'strategy = "single-session"\neffort = "high"\n'
                '[tools]\nsource = "none"\nallowed = ["Read"]\n',
                encoding="utf-8",
            )
            args = types.SimpleNamespace(
                command="run",
                bank="b",
                dry_run=True,
                limit=None,
                tasks=None,
                repeats=1,
                tasks_dir=tmp_p / "tasks",
                scenarios_dir=tmp_p / "scenarios",
                ledger_dir=tmp_p / "ledger",
                include_holdout=False,
                max_spawn_usd=None,
                legacy_max_budget_usd=None,
                max_run_usd=None,
                skip_bank_validation=True,
                skip_arming_check=True,
                skip_credential_check=True,
                no_lock=True,
                lock_wait_s=None,
                **extra,
            )
            with mock.patch("fathom.cli.run_matrix", return_value=EXIT_OK) as rm:
                self.assertEqual(_cmd_run(args), EXIT_OK)
        return rm.call_args.kwargs

    def test_cmd_run_hands_the_resume_command_to_run_matrix(self):
        resume = self._cmd_run_kwargs()["resume_cmd"]
        self.assertTrue(resume.startswith("fathom run b --repeats 1 --tasks-dir "), resume)
        self.assertIn("--ledger-dir", resume)

    def test_cmd_run_hands_the_interleave_flag_to_run_matrix(self):
        self.assertIs(self._cmd_run_kwargs()["interleave"], False)
        kwargs = self._cmd_run_kwargs(interleave=True)
        self.assertIs(kwargs["interleave"], True)
        self.assertTrue(kwargs["resume_cmd"].endswith(" --interleave"), kwargs["resume_cmd"])


# ---------------------------------------------------------------------------
# Comparator dependency (FATH-B58)
# ---------------------------------------------------------------------------


def _errored_result(task=None, ws=None, sc=None) -> TrialResult:
    return TrialResult(
        status=TrialStatus.ERRORED,
        runs=[_ok_run()],
        pin_level=PIN_STRONG,
        detail="engine exited 1",
    )


class TestComparatorDependency(_Base):
    """An arm with `comparator = "bare"` is bought for a cell (task, repeat) only after
    bare completed that cell, in an earlier invocation or this one. Otherwise the cell is
    blocked: no executor, no spawn, no ledger row, and a count in the run summary."""

    def setUp(self):
        super().setUp()
        self.nudge = _make_scenario("nudge", config_hash="c" * 64, comparator="bare")
        self.factory_calls: list[str] = []

    def _executors(self, **result_fns) -> dict[str, StubExecutor]:
        return {
            name: StubExecutor(result_fn=result_fns.get(name))
            for name in ("bare", "single-long", "nudge")
        }

    def _factory(self, executors: dict[str, StubExecutor]):
        def factory(sc):
            self.factory_calls.append(sc.name)
            return executors[sc.name]

        return factory

    def _rows_with_hash(self, config_hash: str) -> list[dict]:
        path = self.ledger_dir / "test-bank.jsonl"
        if not path.exists():
            return []
        rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln]
        return [r for r in rows if r.get("config_hash") == config_hash]

    def test_a_failed_comparator_buys_nothing_for_its_dependent(self):
        executors = self._executors(bare=_errored_result)
        out = _FlushCountingStream()
        code, _ = _run_matrix(
            self.bank,
            [self.sc_a, self.nudge],
            repeats=2,
            ledger_dir=self.ledger_dir,
            out=out,
            executor_factory=self._factory(executors),
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(len(executors["bare"].calls), 4)
        self.assertEqual(len(executors["nudge"].calls), 0, "the dependent arm spawned")
        self.assertNotIn("nudge", self.factory_calls)
        self.assertEqual(self._rows_with_hash("c" * 64), [], "a ledger row for a blocked cell")
        blocked = out.flushed_lines("blocked:")
        self.assertEqual(len(blocked), 4)
        self.assertTrue(all(flushed for _, flushed in blocked))
        self.assertEqual(
            blocked[0][0],
            "blocked: nudge/task-1 r0 — comparator bare has no completed trial for this cell; "
            "nothing spent",
        )
        fields = _summary_fields(out.getvalue())
        self.assertEqual(fields["blocked"], 4)
        self.assertEqual((fields["completed"], fields["errored"]), (0, 4))
        self.assertEqual(fields["not_started"], 0)
        self.assertAlmostEqual(fields["usd"], 0.20, msg="only the comparator's spawns cost")

    def test_only_the_cells_the_comparator_missed_are_blocked(self):
        def bare(task, ws, sc):
            bare.n += 1
            return _errored_result() if bare.n == 1 else _ok_result()

        bare.n = 0
        executors = self._executors(bare=bare)
        out = io.StringIO()
        code, _ = _run_matrix(
            self.bank,
            [self.sc_a, self.nudge],
            repeats=2,
            ledger_dir=self.ledger_dir,
            out=out,
            executor_factory=self._factory(executors),
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(len(executors["nudge"].calls), 3)
        self.assertEqual(
            [ln for ln in out.getvalue().splitlines() if ln.startswith("blocked:")],
            [
                (
                    "blocked: nudge/task-1 r0 — comparator bare has no completed trial for "
                    "this cell; nothing spent"
                )
            ],
        )
        fields = _summary_fields(out.getvalue())
        self.assertEqual((fields["completed"], fields["errored"], fields["blocked"]), (6, 1, 1))

    def test_a_comparator_completed_in_an_earlier_ledger_lets_the_dependent_run(self):
        _run_matrix(self.bank, [self.sc_a], repeats=2, ledger_dir=self.ledger_dir)
        executors = self._executors()
        code, text = _run_matrix(
            self.bank,
            [self.sc_a, self.nudge],
            repeats=2,
            ledger_dir=self.ledger_dir,
            executor_factory=self._factory(executors),
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(len(executors["bare"].calls), 0, "bare was already done")
        self.assertEqual(len(executors["nudge"].calls), 4)
        self.assertNotIn("blocked:", text)
        fields = _summary_fields(text)
        self.assertEqual((fields["completed"], fields["skipped"], fields["blocked"]), (4, 4, 0))
        self.assertEqual(len(self._rows_with_hash("c" * 64)), 8, "4 run rows and 4 trial rows")

    def test_the_comparator_runs_before_its_dependent(self):
        shared = StubExecutor()
        code, text = _run_matrix(
            self.bank,
            [self.nudge, self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
            executor_factory=lambda sc: shared,
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(
            [c.scenario.name for c in shared.calls], ["bare", "bare", "nudge", "nudge"]
        )
        self.assertIn("arms:     bare [aaaaaaaaaaaa], nudge [cccccccccccc]\n", text)
        self.assertIn(
            "\ndepends:  nudge on bare (a cell runs only after bare completed the same task "
            "and repeat)\n",
            text,
        )

    def test_the_depends_line_is_on_the_dry_run_plan(self):
        code, text = _run_matrix(
            self.bank, [self.sc_a, self.nudge], ledger_dir=self.ledger_dir, dry_run=True
        )
        self.assertEqual(code, EXIT_OK)
        lines = text.splitlines()
        self.assertEqual(
            lines[2],
            "depends:  nudge on bare (a cell runs only after bare completed the same task and "
            "repeat)",
        )
        self.assertTrue(lines[3].startswith("planned:  8 trials (0 already done)"))

    def test_without_the_key_the_plan_is_byte_identical(self):
        code, text = _run_matrix(
            self.bank, self.scenarios, repeats=2, ledger_dir=self.ledger_dir, dry_run=True
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(
            text,
            "fathom run: bank=test-bank  scenarios=2  tasks=2  repeats=2\n"
            "arms:     bare [aaaaaaaaaaaa], single-long [bbbbbbbbbbbb]\n"
            "planned:  8 trials (0 already done)  ceiling: $40.00\n"
            "[dry-run] no spawns\n",
        )

    def test_without_the_key_the_call_order_is_untouched(self):
        shared = StubExecutor()
        code, text = _run_matrix(
            self.bank,
            [self.sc_b, self.sc_a],
            repeats=1,
            ledger_dir=self.ledger_dir,
            executor_factory=lambda sc: shared,
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(
            [(c.scenario.name, c.task.id) for c in shared.calls],
            [
                ("single-long", "task-1"),
                ("single-long", "task-2"),
                ("bare", "task-1"),
                ("bare", "task-2"),
            ],
        )
        self.assertNotIn("depends:", text)
        self.assertNotIn("blocked:", text)
        self.assertIsNone(_summary_fields(text)["blocked"])

    def _refused(self, scenarios: list[ResolvedScenario], **kw) -> tuple[int, str]:
        from contextlib import redirect_stderr

        err = io.StringIO()
        shared = StubExecutor()
        with redirect_stderr(err):
            code, out = _run_matrix(
                self.bank,
                scenarios,
                ledger_dir=self.ledger_dir,
                executor_factory=lambda sc: shared,
                **kw,
            )
        self.assertEqual(shared.calls, [])
        self.assertNotIn("planned:", out)
        return code, err.getvalue()

    def test_an_unknown_comparator_returns_1_on_dry_run(self):
        missing = _make_scenario("nudge", config_hash="c" * 64, comparator="missing")
        code, err = self._refused([self.sc_a, missing], dry_run=True)
        self.assertEqual(code, 1)
        self.assertIn("'nudge'", err)
        self.assertIn("'missing'", err)

    def test_an_unknown_comparator_returns_1_on_a_real_run(self):
        missing = _make_scenario("nudge", config_hash="c" * 64, comparator="missing")
        code, _ = self._refused([self.sc_a, missing])
        self.assertEqual(code, 1)

    def test_a_comparator_on_itself_returns_1(self):
        selfish = _make_scenario("nudge", config_hash="c" * 64, comparator="nudge")
        code, err = self._refused([self.sc_a, selfish], dry_run=True)
        self.assertEqual(code, 1)
        self.assertIn("itself", err)

    def test_a_comparator_cycle_returns_1(self):
        one = _make_scenario("one", config_hash="c" * 64, comparator="two")
        two = _make_scenario("two", config_hash="d" * 64, comparator="one")
        code, err = self._refused([self.sc_a, one, two], dry_run=True)
        self.assertEqual(code, 1)
        self.assertIn("cycle", err)


class TestInterleave(unittest.TestCase):
    """``--interleave``: repeat-major trial order, opt-in.

    The default plan is arm by arm, so a trial list cut short (``--limit``, a stop, a
    spend rail) holds every repeat of the first arm and none of the last. With the flag the
    plan runs repeat 0 of every arm before repeat 1 of any, so a partial run still compares
    the arms.
    """

    # The dry run and the call order of today's plan: 2 arms, 1 task, 2 repeats, with
    # the flag absent. Captured from the code before the flag existed.
    _DEFAULT_DRY_RUN = (
        "fathom run: bank=test-bank  scenarios=2  tasks=1  repeats=2\n"
        "arms:     bare [aaaaaaaaaaaa], nudge [bbbbbbbbbbbb]\n"
        "planned:  4 trials (0 already done)  ceiling: $20.00\n"
        "[dry-run] no spawns\n"
    )
    _DEFAULT_ORDER = ("bare/add r0", "bare/add r1", "nudge/add r0", "nudge/add r1")
    _ORDER_LINE = (
        "order:    interleaved (repeat, then arm, then task); "
        "--limit keeps the first N of this order"
    )

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.task = _make_task("add", Path(self._tmp))
        self.bank = _make_bank("test-bank", [self.task])
        self.bare = _make_scenario("bare", config_hash="a" * 64)
        self.nudge = _make_scenario("nudge", config_hash="b" * 64)

    def _ledger(self) -> Path:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(d), ignore_errors=True)
        return d

    def _order(self, output: str) -> list[str]:
        """The cells in the order they ran, from the progress lines."""
        return [
            line.split()[3] + " " + line.split()[4]
            for line in output.splitlines()
            if line.startswith("trial done:")
        ]

    def _run(self, repeats=2, scenarios=None, **kw):
        kw.setdefault("ledger_dir", self._ledger())
        return _run_matrix(self.bank, scenarios or [self.bare, self.nudge], repeats, **kw)

    def test_without_the_flag_the_dry_run_is_unchanged(self):
        _, output = self._run(dry_run=True)
        self.assertEqual(output, self._DEFAULT_DRY_RUN)

    def test_without_the_flag_the_call_order_is_unchanged(self):
        calls: list[str] = []

        def factory(sc):
            return StubExecutor(result_fn=lambda t, w, s: calls.append(s.name) or _ok_result())

        _, output = self._run(executor_factory=factory)
        self.assertEqual(self._order(output), list(self._DEFAULT_ORDER))
        self.assertEqual(calls, ["bare", "bare", "nudge", "nudge"])
        self.assertNotIn("order:", output)

    def test_with_the_flag_the_arms_alternate_within_a_repeat_ahead_of_the_next(self):
        calls: list[str] = []

        def factory(sc):
            return StubExecutor(result_fn=lambda t, w, s: calls.append(s.name) or _ok_result())

        _, output = self._run(interleave=True, executor_factory=factory)
        self.assertEqual(calls, ["bare", "nudge", "bare", "nudge"])
        self.assertEqual(
            self._order(output), ["bare/add r0", "nudge/add r0", "bare/add r1", "nudge/add r1"]
        )

    def test_with_the_flag_a_repeat_runs_its_tasks_in_bank_order_before_the_next_arm(self):
        bank = _make_bank("test-bank", [self.task, _make_task("sub", Path(self._tmp))])
        _, output = _run_matrix(
            bank,
            [self.bare, self.nudge],
            2,
            ledger_dir=self._ledger(),
            interleave=True,
        )
        self.assertEqual(
            self._order(output),
            [
                "bare/add r0",
                "bare/sub r0",
                "nudge/add r0",
                "nudge/sub r0",
                "bare/add r1",
                "bare/sub r1",
                "nudge/add r1",
                "nudge/sub r1",
            ],
        )

    def test_with_the_flag_limit_of_arms_times_tasks_runs_repeat_zero_of_every_arm(self):
        calls: list[str] = []

        def factory(sc):
            return StubExecutor(result_fn=lambda t, w, s: calls.append(s.name) or _ok_result())

        _, output = self._run(repeats=3, interleave=True, limit=2, executor_factory=factory)
        self.assertEqual(calls, ["bare", "nudge"])
        self.assertEqual(self._order(output), ["bare/add r0", "nudge/add r0"])

    def test_without_the_flag_the_same_limit_cuts_the_last_arm_off(self):
        _, output = self._run(repeats=3, limit=2)
        self.assertEqual(self._order(output), ["bare/add r0", "bare/add r1"])

    def test_a_comparator_still_runs_ahead_of_its_dependent_in_each_repeat(self):
        dependent = _make_scenario("nudge", config_hash="b" * 64, comparator="bare")
        # Listed dependent-first: the comparator ordering puts bare first, and the
        # interleaving keeps it.
        _, output = self._run(scenarios=[dependent, self.bare], interleave=True)
        self.assertEqual(
            self._order(output), ["bare/add r0", "nudge/add r0", "bare/add r1", "nudge/add r1"]
        )
        self.assertNotIn("blocked:", output)

    def test_the_resume_keys_written_are_the_same_with_and_without_the_flag(self):
        plain, flagged = self._ledger(), self._ledger()
        self._run(repeats=3, ledger_dir=plain)
        self._run(repeats=3, ledger_dir=flagged, interleave=True)
        keys = _ledger.completed_keys("test-bank", ledger_dir=plain)
        self.assertEqual(len(keys), 6)
        self.assertEqual(_ledger.completed_keys("test-bank", ledger_dir=flagged), keys)

    def test_the_dry_run_names_the_order_and_the_first_cells(self):
        _, output = self._run(dry_run=True, interleave=True)
        self.assertIn(self._ORDER_LINE, output.splitlines())
        self.assertIn("first:    bare/add r0, nudge/add r0, bare/add r1, nudge/add r1", output)
        # The count line is the one the default prints, whole.
        self.assertIn("planned:  4 trials (0 already done)  ceiling: $20.00", output)

    def test_the_first_cells_follow_the_limit_and_stop_at_six(self):
        _, output = self._run(repeats=5, dry_run=True, interleave=True, limit=2)
        self.assertIn("first:    bare/add r0, nudge/add r0\n", output)
        _, longer = self._run(repeats=5, dry_run=True, interleave=True)
        first = next(line for line in longer.splitlines() if line.startswith("first:"))
        self.assertEqual(first.count(" r"), 6)
        self.assertTrue(first.endswith(", ..."))

    def test_the_flag_is_on_the_run_parser_and_off_by_default(self):
        from fathom.cli import _build_parser

        parser = _build_parser()
        self.assertFalse(parser.parse_args(["run", "b"]).interleave)
        self.assertTrue(parser.parse_args(["run", "b", "--interleave"]).interleave)

    def test_a_resume_command_keeps_the_flag_when_it_was_given(self):
        from fathom.cli import _resume_command

        args = types.SimpleNamespace(
            bank="b",
            repeats=3,
            tasks=None,
            include_holdout=False,
            max_run_usd=None,
            data_root=None,
            home=None,
            interleave=True,
        )
        self.assertEqual(
            _resume_command(args, spawn_cap=None), "fathom run b --repeats 3 --interleave"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
