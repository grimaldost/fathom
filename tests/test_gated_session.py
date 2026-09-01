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
from fathom.strategies.gated_session import GatedSessionExecutor, expand_gate_placeholders
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


# --- run-time placeholder expansion in scenario gate commands -----------------
#
# A harness-side probe lives in the TASK directory and the gate runs with cwd =
# the trial workspace, so the only forms that resolve are a machine-absolute path
# (unportable, uncommittable) or a placeholder expanded per trial. The committed
# `haiku-gate-sg` arm shipped the placeholder-shaped literal
# `python /path/to/fathom/.../type_probe.py .`, which the shell ran verbatim: the
# probe never executed and the arm silently degraded to the plain gate arm.

_PROBE = "import os,sys; sys.exit(0 if os.path.exists(os.path.join(sys.argv[1],'ok')) else 1)"


def test_task_dir_placeholder_resolves_to_a_runnable_probe():
    """`${task_dir}` reaches a script that no relative path from the workspace could."""
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir, ws = Path(td), Path(wd)
        (task_dir / "probe.py").write_text(_PROBE, encoding="utf-8")
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=task_dir)
        # Probe green only once the impl spawn writes `ok` into the workspace.
        runner = _StubRunner(write_done_on_call=99, files_by_call={1: "ok"})
        ex = GatedSessionExecutor(extra_gate_cmds=['python "${task_dir}/probe.py" "${workspace}"'])
        res = ex.run_trial(task, ws, None, runner)
    assert runner.calls == 1
    assert "first=green" in res.detail and "final=green" in res.detail


def test_unexpanded_placeholder_would_fail_the_gate():
    """Guards the regression: an unsubstituted literal path is a red gate, not a green one.

    Without expansion the same arm runs `python /path/to/.../probe.py .`, which the
    shell resolves to nothing — so this asserts the failure mode is loud (red +
    fix spawns) rather than the silent pass the broken arm produced.
    """
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir, ws = Path(td), Path(wd)
        (task_dir / "probe.py").write_text(_PROBE, encoding="utf-8")
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=task_dir)
        runner = _StubRunner(write_done_on_call=99, files_by_call={1: "ok"})
        ex = GatedSessionExecutor(
            max_fix_attempts=1, extra_gate_cmds=["python /path/to/fathom/probe.py ."]
        )
        res = ex.run_trial(task, ws, None, runner)
    assert "final=red" in res.detail


# --- the extra gate's own output reaches the ledger ---------------------------
#
# `first=red` cannot say which tool produced the red, which build of it ran, or
# whether it ran at all — and for an arm whose extra gate is an external tool that
# provenance IS the attestation. On green the output used to be dropped entirely;
# on red it went into the fix prompt and nowhere else.

_ECHO_GATE = "python -c \"import sys; print('gate via: TESTPIN'); sys.exit(0)\""
_LOUD_GATE = "python -c \"print('y' * 3000)\""


def test_extra_gate_output_reaches_detail_on_green():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner(write_done_on_call=1)
        ex = GatedSessionExecutor(extra_gate_cmds=[_ECHO_GATE])
        res = ex.run_trial(_task(ws), ws, None, runner)
    assert "first=green" in res.detail
    assert "extra-gate first: gate via: TESTPIN" in res.detail


def test_extra_gate_not_reached_when_the_task_gate_reds_first():
    """The task's own gate short-circuits the list — say so, don't imply a silent run."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner(write_done_on_call=99)  # task gate never greens
        ex = GatedSessionExecutor(max_fix_attempts=0, extra_gate_cmds=[_ECHO_GATE])
        res = ex.run_trial(_task(ws), ws, None, runner)
    assert "final=red" in res.detail
    assert "extra-gate first: <not run" in res.detail
    assert "TESTPIN" not in res.detail


def test_extra_gate_excerpt_is_bounded_and_marks_what_it_dropped():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner(write_done_on_call=1)
        ex = GatedSessionExecutor(extra_gate_cmds=[_LOUD_GATE])
        res = ex.run_trial(_task(ws), ws, None, runner)
    assert "chars omitted" in res.detail
    assert len(res.detail) < 1500


def test_extra_gate_records_both_rounds_when_a_fix_ran():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner(write_done_on_call=1, files_by_call={2: "done2"})
        ex = GatedSessionExecutor(max_fix_attempts=2, extra_gate_cmds=[_GATE2])
        res = ex.run_trial(_task(ws), ws, None, runner)
    assert "fixes=1" in res.detail
    assert "extra-gate first:" in res.detail and "extra-gate final:" in res.detail


def test_commands_without_placeholders_are_byte_identical():
    """No placeholder means no rewrite — committed resume keys and gates cannot move."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        for cmd in (_GATE, _GATE2, "python -m unittest discover -s tests -t ."):
            assert expand_gate_placeholders(cmd, task_dir=ws, workspace=ws) == cmd


if __name__ == "__main__":
    for fn in (
        test_gate_green_on_first_check_is_one_spawn,
        test_gate_red_then_green_drives_one_fix,
        test_fix_attempts_are_capped_and_still_scored,
        test_no_gate_degrades_to_single_spawn,
        test_extra_gate_output_reaches_detail_on_green,
        test_extra_gate_not_reached_when_the_task_gate_reds_first,
        test_extra_gate_excerpt_is_bounded_and_marks_what_it_dropped,
        test_extra_gate_records_both_rounds_when_a_fix_ran,
        test_task_dir_placeholder_resolves_to_a_runnable_probe,
        test_unexpanded_placeholder_would_fail_the_gate,
        test_commands_without_placeholders_are_byte_identical,
    ):
        fn()
        print(f"ok {fn.__name__}")
    print("all gated_session tests passed")
