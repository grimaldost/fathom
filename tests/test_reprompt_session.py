"""Unit tests for the RepromptSessionExecutor (iteration-matched control, FM-6).

A stub Runner returns a scripted sequence of exit statuses; the strategy makes
exactly two UNCONDITIONAL spawns (implementation + one generic re-verify) unless the
first spawn is infrastructure. Stdlib-runnable.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.strategies.base import TrialStatus
from fathom.strategies.reprompt_session import RepromptSessionExecutor
from fathom.taskbank import Task


class _StubRunner:
    """Returns a scripted status per call; records call count."""

    def __init__(self, statuses) -> None:
        self.calls = 0
        self.statuses = statuses

    def execute(self, prompt, workspace, scenario, max_turns=None):  # noqa: ANN001, ARG002
        st = self.statuses[self.calls]
        self.calls += 1
        return RunRecord(status=st, duration_s=1.0, num_turns=1)


def _task(ws: Path) -> Task:
    return Task(id="t", instruction="x", limits={}, verify={"entry": "verify.py"}, task_dir=ws)


def test_makes_exactly_two_unconditional_spawns():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner([ExitStatus.OK, ExitStatus.OK])
        res = RepromptSessionExecutor().run_trial(_task(ws), ws, None, runner)
    assert runner.calls == 2
    assert len(res.runs) == 2
    assert res.status is TrialStatus.COMPLETED
    assert "reprompt" in res.detail


def test_first_spawn_infrastructure_stops_before_reprompt():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner([ExitStatus.INFRASTRUCTURE, ExitStatus.OK])
        res = RepromptSessionExecutor().run_trial(_task(ws), ws, None, runner)
    assert runner.calls == 1
    assert len(res.runs) == 1
    assert res.status is TrialStatus.INFRASTRUCTURE


def test_errored_impl_still_reprompts_and_scores_errored():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner([ExitStatus.ERROR, ExitStatus.OK])
        res = RepromptSessionExecutor().run_trial(_task(ws), ws, None, runner)
    assert runner.calls == 2
    assert res.status is TrialStatus.ERRORED


def test_second_spawn_infrastructure_is_infrastructure():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner([ExitStatus.OK, ExitStatus.INFRASTRUCTURE])
        res = RepromptSessionExecutor().run_trial(_task(ws), ws, None, runner)
    assert runner.calls == 2
    assert res.status is TrialStatus.INFRASTRUCTURE


if __name__ == "__main__":
    for fn in (
        test_makes_exactly_two_unconditional_spawns,
        test_first_spawn_infrastructure_stops_before_reprompt,
        test_errored_impl_still_reprompts_and_scores_errored,
        test_second_spawn_infrastructure_is_infrastructure,
    ):
        fn()
        print(f"ok {fn.__name__}")
    print("all reprompt_session tests passed")
