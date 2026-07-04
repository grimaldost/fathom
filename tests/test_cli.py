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
    """Helper: call run_matrix with stubs filled in and capture stdout."""
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
