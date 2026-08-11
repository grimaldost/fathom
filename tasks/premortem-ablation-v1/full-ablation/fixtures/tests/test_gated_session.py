"""Unit tests for the GatedSessionExecutor (bare+gate ablation arm).

A stub Runner stands in for the model; a real subprocess gate (`python -c ...`)
checks for a `done` marker the stub writes on a chosen call, so the fix loop is
exercised deterministically without any model spawn. Stdlib-runnable.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.strategies.base import TrialStatus
from fathom.strategies.gated_session import GatedSessionExecutor
from fathom.taskbank import Task

# Gate passes iff a file named `done` exists in the workspace (cwd).
_GATE = "python -c \"import os,sys; sys.exit(0 if os.path.exists('done') else 1)\""


class _StubRunner:
    """Creates the `done` marker on its Nth execute call; records call count."""

    def __init__(
        self, write_done_on_call: int, files_by_call: dict[int, str] | None = None
    ) -> None:
        self.calls = 0
        self.write_done_on_call = write_done_on_call
        self.files_by_call = files_by_call or {}
        self.prompts: list[str] = []

    def execute(self, prompt, workspace, scenario, max_turns=None):  # noqa: ANN001, ARG002
        self.calls += 1
        self.prompts.append(prompt)
        if self.calls == self.write_done_on_call:
            (Path(workspace) / "done").write_text("ok", encoding="utf-8")
        name = self.files_by_call.get(self.calls)
        if name:
            (Path(workspace) / name).write_text("ok", encoding="utf-8")
        return RunRecord(status=ExitStatus.OK, duration_s=1.0, num_turns=1)


def _task(ws: Path) -> Task:
    return Task(
        id="t",
        instruction="implement it",
        limits={},
        verify={"entry": "verify.py"},
        task_dir=ws,
        gate={"run": _GATE},
    )


def test_gate_green_on_first_check_is_one_spawn():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner(write_done_on_call=1)  # impl already satisfies the gate
        res = GatedSessionExecutor(max_fix_attempts=2).run_trial(_task(ws), ws, None, runner)
    assert runner.calls == 1
    assert len(res.runs) == 1
    assert res.status is TrialStatus.COMPLETED
    assert "first=green" in res.detail and "final=green" in res.detail


def test_gate_red_then_green_drives_one_fix():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner(write_done_on_call=2)  # green only after one fix spawn
        res = GatedSessionExecutor(max_fix_attempts=2).run_trial(_task(ws), ws, None, runner)
    assert runner.calls == 2
    assert len(res.runs) == 2
    assert res.status is TrialStatus.COMPLETED
    assert "first=red" in res.detail and "final=green" in res.detail and "fixes=1" in res.detail


def test_fix_attempts_are_capped_and_still_scored():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner(write_done_on_call=99)  # never satisfies the gate
        res = GatedSessionExecutor(max_fix_attempts=1).run_trial(_task(ws), ws, None, runner)
    # impl + exactly 1 fix (capped); trial still COMPLETED (workspace is gradeable)
    assert runner.calls == 2
    assert len(res.runs) == 2
    assert res.status is TrialStatus.COMPLETED
    assert "final=red" in res.detail


def test_no_gate_degrades_to_single_spawn():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=ws)
        runner = _StubRunner(write_done_on_call=99)
        res = GatedSessionExecutor().run_trial(task, ws, None, runner)
    assert runner.calls == 1
    assert len(res.runs) == 1
    assert res.status is TrialStatus.COMPLETED


_GATE2 = "python -c \"import os,sys; sys.exit(0 if os.path.exists('done2') else 1)\""


def test_extra_gate_red_drives_fix_and_names_failing_cmd():
    # Task gate green from call 1; the EXTRA (scenario-level) gate red until the
    # fix spawn (call 2) writes done2 -> composite gate forces exactly one fix.
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner(write_done_on_call=1, files_by_call={2: "done2"})
        ex = GatedSessionExecutor(max_fix_attempts=2, extra_gate_cmds=[_GATE2])
        res = ex.run_trial(_task(ws), ws, None, runner)
    assert runner.calls == 2
    assert "first=red" in res.detail and "final=green" in res.detail and "fixes=1" in res.detail
    # The fix prompt must carry the failing command's output header ("$ <cmd>").
    assert any("done2" in p for p in runner.prompts[1:])


def test_extra_gate_runs_without_task_gate():
    # A task with NO [gate] still gets the scenario-level extra gate.
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=ws)
        runner = _StubRunner(write_done_on_call=99, files_by_call={1: "done2"})
        ex = GatedSessionExecutor(extra_gate_cmds=[_GATE2])
        res = ex.run_trial(task, ws, None, runner)
    assert runner.calls == 1
    assert "first=green" in res.detail and "final=green" in res.detail


if __name__ == "__main__":
    for fn in (
        test_gate_green_on_first_check_is_one_spawn,
        test_gate_red_then_green_drives_one_fix,
        test_fix_attempts_are_capped_and_still_scored,
        test_no_gate_degrades_to_single_spawn,
    ):
        fn()
        print(f"ok {fn.__name__}")
    print("all gated_session tests passed")
