"""Tests for src/fathom/strategies/{base,single_session}.py.

Stdlib-runnable:
    python tests/test_strategies.py
Via pytest:
    uv run pytest tests/test_strategies.py

The Runner is a stub: no real spawn runs here (real-spawn isolation is the smoke
gate's job, spec §11).
"""

import sys
import tempfile
import types
import unittest
from pathlib import Path

# Allow `python tests/test_strategies.py` from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.adapters.claude_cli import cleanup_dir
from fathom.scenario import LimitsOverride, ResolvedScenario, ToolsConfig
from fathom.strategies.base import (
    PIN_SERIES,
    PIN_STRONG,
    StrategyExecutor,
    TrialResult,
    TrialStatus,
)
from fathom.strategies.single_session import SingleSessionExecutor
from fathom.taskbank import Task

# ---------------------------------------------------------------------------
# Shared fixtures / factories
# ---------------------------------------------------------------------------


def _scenario(*, model="claude-opus-4-8", effort="high", trial_timeout_s=3600):
    return ResolvedScenario(
        name="single",
        adapter="claude-cli",
        model=model,
        strategy="single-session",
        effort=effort,
        tools=ToolsConfig(source="none"),
        limits=LimitsOverride(trial_timeout_s=trial_timeout_s),
        model_id=None,
        tool_repo_sha=None,
        tool_invocation_cmd=None,
        config_hash="x" * 64,
    )


def _ok_record(**kw):
    base = {
        "status": ExitStatus.OK,
        "tokens_in": 10,
        "tokens_out": 5,
        "num_turns": 3,
        "duration_s": 1.5,
        "cost_usd_est": 0.01,
        "model_id": "claude-opus-4-8-exact",
    }
    base.update(kw)
    return RunRecord(**base)


class StubRunner:
    """Records every execute() call; replays one preconfigured RunRecord."""

    def __init__(self, record):
        self.record = record
        self.calls = []

    def execute(self, prompt, workspace, scenario, max_turns=None):
        self.calls.append(
            types.SimpleNamespace(
                prompt=prompt, workspace=workspace, scenario=scenario, max_turns=max_turns
            )
        )
        return self.record


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class TestProtocol(unittest.TestCase):
    def test_the_executor_satisfies_the_protocol(self):
        self.assertIsInstance(SingleSessionExecutor(), StrategyExecutor)


# ---------------------------------------------------------------------------
# Single-session: exactly one Runner call per trial
# ---------------------------------------------------------------------------


class TestSingleSession(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="fathom-ws-"))
        self.addCleanup(cleanup_dir, str(self.workspace))
        self.task = Task(
            id="t1",
            instruction="do it",
            limits={},
            verify={"entry": "verify.py"},
            task_dir=self.workspace,
        )

    def _run(self, record):
        runner = StubRunner(record)
        result = SingleSessionExecutor().run_trial(self.task, self.workspace, _scenario(), runner)
        return runner, result

    def test_exactly_one_run_per_trial(self):
        runner, result = self._run(_ok_record())
        self.assertEqual(len(runner.calls), 1, "single-session must call the Runner exactly once")
        self.assertEqual(len(result.runs), 1)
        self.assertEqual(result.pin_level, PIN_STRONG)
        self.assertEqual(result.status, TrialStatus.COMPLETED)
        self.assertEqual(runner.calls[0].prompt, "do it")

    def test_error_record_maps_to_errored(self):
        _, result = self._run(_ok_record(status=ExitStatus.ERROR, result_text="boom"))
        self.assertEqual(result.status, TrialStatus.ERRORED)
        self.assertTrue(result.scored)

    def test_timeout_record_maps_to_errored(self):
        _, result = self._run(_ok_record(status=ExitStatus.TIMEOUT))
        self.assertEqual(result.status, TrialStatus.ERRORED)

    def test_infrastructure_record_not_scored(self):
        _, result = self._run(_ok_record(status=ExitStatus.INFRASTRUCTURE))
        self.assertEqual(result.status, TrialStatus.INFRASTRUCTURE)
        self.assertTrue(result.is_infrastructure)
        self.assertFalse(result.scored)

    def test_passes_task_max_turns_to_runner(self):
        """The task's turn budget (task.limits.max_turns) must reach the spawn —
        otherwise the adapter's lower default caps and truncates multi-step tasks."""
        task = Task(
            id="t",
            instruction="go",
            limits={"max_turns": 60},
            verify={"entry": "verify.py"},
            task_dir=self.workspace,
        )
        runner = StubRunner(_ok_record())
        SingleSessionExecutor().run_trial(task, self.workspace, _scenario(), runner)
        self.assertEqual(runner.calls[0].max_turns, 60)

    def test_passes_none_when_task_sets_no_max_turns(self):
        runner = StubRunner(_ok_record())  # self.task has limits={}
        SingleSessionExecutor().run_trial(self.task, self.workspace, _scenario(), runner)
        self.assertIsNone(runner.calls[0].max_turns)


# ---------------------------------------------------------------------------
# TrialResult helpers
# ---------------------------------------------------------------------------


class TestTrialResult(unittest.TestCase):
    def test_infrastructure_not_scored(self):
        r = TrialResult(status=TrialStatus.INFRASTRUCTURE, runs=[], pin_level=PIN_SERIES)
        self.assertTrue(r.is_infrastructure)
        self.assertFalse(r.scored)

    def test_errored_is_scored(self):
        r = TrialResult(status=TrialStatus.ERRORED, runs=[], pin_level=PIN_STRONG)
        self.assertFalse(r.is_infrastructure)
        self.assertTrue(r.scored)


if __name__ == "__main__":
    unittest.main(verbosity=2)
