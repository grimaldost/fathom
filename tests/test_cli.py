"""Tests for src/fathom/cli.py — stdlib-runnable.

Run via pytest or directly:  python tests/test_cli.py

All executors/runners/stage/verifier are stubbed — no real spawns.
"""

from __future__ import annotations

import io
import pathlib
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

import fathom.ledger as _ledger
from fathom.adapters.base import ExitStatus
from fathom.adapters.base import RunRecord as AdapterRunRecord
from fathom.cli import EXIT_INFRASTRUCTURE, EXIT_OK, run_matrix
from fathom.grading.verifier import VerifierResult
from fathom.scenario import LimitsOverride, ResolvedScenario, ToolsConfig
from fathom.strategies.base import PIN_STRONG, TrialResult, TrialStatus
from fathom.taskbank import Bank, Task


# ---------------------------------------------------------------------------
# Stub factories
# ---------------------------------------------------------------------------


def _make_scenario(name: str = "bare", config_hash: str = "a" * 64, **kw) -> ResolvedScenario:
    defaults: dict = dict(
        adapter="claude-cli",
        model="claude-opus-4-8",
        strategy="single-session",
        effort="high",
        tools=ToolsConfig(source="none"),
        limits=LimitsOverride(),
        model_id=None,
        tool_repo_sha=None,
        tool_invocation_cmd=None,
    )
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
# Per-task verify timeout plumbing (ADR-0008 §5 / FM-8): real-anchor verifiers
# shell out to a third-party venv's pytest whose import+collect exceeds 60s.
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

    def test_prints_ceiling(self):
        _, output = _run_matrix(self.bank, self.scenarios, ledger_dir=self.ledger_dir, dry_run=True)
        self.assertIn("ceiling:", output)

    def test_prints_dry_run_marker(self):
        _, output = _run_matrix(self.bank, self.scenarios, ledger_dir=self.ledger_dir, dry_run=True)
        self.assertIn("[dry-run]", output)


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
        kw = dict(
            executor_factory=lambda sc: StubExecutor(),
            runner_factory=lambda sc: StubRunner(),
            stage_task_fn=_stub_stage,
            verifier_fn=_stub_verifier,
            skip_bank_validation=True,
            ledger_dir=self.ledger_dir,
        )
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
            name="pyeng-skill",
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

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
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
            name="humble-only",
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
            Path(d, "plugin.json").write_text("{}")
            runner = _default_runner_factory(self._resolved_with_mounts((d,)))
        self.assertEqual(runner.plugin_dirs, (d,))

    def test_valid_mount_produces_no_warning(self):
        import contextlib
        import tempfile

        from fathom.cli import _default_runner_factory

        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            Path(d, "plugin.json").write_text("{}")
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
        with tempfile.TemporaryDirectory() as d:
            # Directory exists but is empty — not a usable plugin mount
            with contextlib.redirect_stderr(buf):
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
            proc = subprocess.run(
                [sys.executable, "-m", "fathom", "report", "toy"],
                cwd=str(dp),
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

        def __init__(self, obs) -> None:  # noqa: ANN001
            self.obs = obs
            self.calls: list[str] = []

        def observe(self, scenario):  # noqa: ANN001, ANN202
            self.calls.append(scenario.name)
            return self.obs

    @staticmethod
    def _obs(**kw):  # noqa: ANN205
        from fathom.arming import ArmingObservation

        base = dict(
            spawn_ok=True,
            init_present=True,
            plugins=(),
            skills=(),
            tools=(),
            mcp_servers=(),
            hooks_fired=(),
            successful_mcp_calls=(),
            denied_tools=(),
            argv=(),
            spawn_env={},
            config_dir_files=(),
            settings_sha=None,
        )
        base.update(kw)
        return ArmingObservation(**base)

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.bank = _make_bank("arming-bank", [_make_task("t1", Path(self._tmp))])
        self.ledger_dir = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
        shutil.rmtree(str(self.ledger_dir), ignore_errors=True)

    def _run(self, scenario, probe, **kw):  # noqa: ANN001, ANN202
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
    every status except INFRASTRUCTURE. 166 usage-limit casualties therefore
    landed as ``status="errored"`` carrying ``{correctness: false, footprint:
    false, trigger_reached: false}``, structurally identical to a trial that ran
    and failed. The first analysis pass read them as real negatives and depressed
    every affected arm's rate on a paid analysis until it was caught by hand.

    Correctness must not depend on every reader independently remembering to
    filter on ``status``.
    """

    def _errored_executor(self):  # noqa: ANN202
        def _fn(task, workspace, scenario):  # noqa: ANN001, ANN202
            return TrialResult(
                status=TrialStatus.ERRORED,
                runs=[_ok_run()],
                pin_level=PIN_STRONG,
                detail="usage limit reached mid-matrix",
            )

        return StubExecutor(_fn)

    def _trials(self, ledger_dir):  # noqa: ANN001, ANN202
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

    This is not hypothetical: a paid trial on `skill-pyeng-v1` errored with
    `verifier error: non-JSON/crash` and the reason was unrecoverable, because the
    verifier imports the agent's modified package and anything that package prints
    at import time lands on the verifier's stdout ahead of the JSON.
    """

    def _crashing_verifier(self, stdout: str, stderr: str = ""):  # noqa: ANN202
        def _fn(entry, workspace, timeout_s=60):  # noqa: ANN001, ANN202
            return VerifierResult(
                outcome="error", criteria=None, stdout=stdout, stderr=stderr, exit_code=1
            )

        return _fn

    def _trials(self):  # noqa: ANN202
        import json

        path = pathlib.Path(self.ledger_dir) / f"{self.bank.name}.jsonl"
        rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
        return [r for r in rows if r.get("kind") == "trial"]

    def test_a_crashed_verifiers_output_is_persisted(self) -> None:
        noise = "Loading timeflow config...\n" + '{"src-layout": true}'
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
            self.assertIn("Loading timeflow config", t.get("verifier_stdout", ""))
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
    def _verifier(outcome: str):  # noqa: ANN205
        def _fn(entry, workspace, timeout_s=60):  # noqa: ANN001, ANN202
            return VerifierResult(
                outcome=outcome,
                criteria={"ok": outcome == "pass"},
                stdout="{}",
                stderr="",
                exit_code=0 if outcome == "pass" else 1,
            )

        return _fn

    def _run(self, outcome: str, **kw):  # noqa: ANN001, ANN202
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
