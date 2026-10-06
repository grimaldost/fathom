"""Unit tests for the GatedSessionExecutor (bare+gate ablation arm).

A stub Runner stands in for the model; a real subprocess gate (`python -c ...`)
checks for a `done` marker the stub writes on a chosen call, so the fix loop is
exercised deterministically without any model spawn. Stdlib-runnable.
"""

import contextlib
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fathom.adapters.base import ExitStatus, RunRecord
from fathom.adapters.claude_cli import hidden_from_children
from fathom.grading.verifier import extract_result_view
from fathom.strategies.base import TrialStatus
from fathom.strategies.gated_session import (
    MASKED_DIR,
    GatedSessionExecutor,
    expand_gate_placeholders,
    mask_gate_text,
    mask_task_dir,
)
from fathom.strategies.single_session import SingleSessionExecutor
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

    def execute(self, prompt, workspace, scenario, max_turns=None):
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
# (unportable, uncommittable) or a placeholder expanded per trial. An arm whose extra
# gate carries a placeholder-shaped literal such as `python /path/to/.../probe.py .`
# has it run verbatim by the shell: the probe never executes and the arm silently
# degrades to the plain gate arm.

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
    fix spawns) rather than a silent pass.
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


# ---------------------------------------------------------------------------
# A gate whose output cannot be decoded must not read as a gate that
# printed nothing.  With `encoding="utf-8"` and no `errors=`, the reader thread
# raises inside subprocess.run, which returns with the exit code intact and the
# offending stream as None; `(None or "") + (None or "")` is `""`, and the fix
# loop is then re-briefed with nothing.  Reproduced here against a real
# subprocess emitting byte 0x97 (the em-dash a cp1252 console stream produced).
# ---------------------------------------------------------------------------


def _emit_bad_byte_script(d: Path) -> Path:
    """A script that writes an invalid-UTF-8 byte to stdout and exits red."""
    script = d / "emit_bad_byte.py"
    script.write_bytes(
        b"import sys\n"
        b'sys.stdout.buffer.write(b"gate said: \\x97 FAILED on 2 checks\\n")\n'
        b"sys.stdout.flush()\n"
        b"sys.exit(1)\n"
    )
    return script


def test_undecodable_gate_output_is_not_an_empty_re_brief():
    """The whole finding: a byte invalid under UTF-8 blanked the fix prompt."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        script = _emit_bad_byte_script(ws)
        cmd = f'"{sys.executable}" "{script}"'
        ok, output = GatedSessionExecutor._run_gate(cmd, ws)
        assert ok is False, "the verdict must stay red — this fix never touches red/green"
        assert output != "", "a gate that printed output must not re-brief with nothing"
        assert "FAILED on 2 checks" in output, output


def test_a_lost_gate_stream_is_a_named_condition_not_an_empty_string():
    """`stdout is None` is a distinct fact from "the gate ran and said nothing"."""
    import subprocess as _sp

    from fathom.strategies import gated_session as gs

    def _lost_stream_run(*a, **kw):
        return _sp.CompletedProcess(args=a[0] if a else "", returncode=1, stdout=None, stderr="")

    # Shadow the NAME in gated_session's namespace, never the subprocess module
    # itself — a test that mutates the stdlib leaks into every test after it.
    real_run = gs._run_shell
    gs._run_shell = _lost_stream_run
    try:
        with tempfile.TemporaryDirectory() as d:
            ok, output = GatedSessionExecutor._run_gate("whatever", Path(d))
    finally:
        gs._run_shell = real_run
    assert ok is False
    assert output == gs.GATE_STREAM_LOST, output


def test_fix_prompt_carries_the_undecodable_output():
    """End to end: the re-brief the fix spawn receives is not blank."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        script = _emit_bad_byte_script(ws)
        task = Task(
            id="t",
            instruction="implement it",
            limits={},
            verify={"entry": "verify.py"},
            task_dir=ws,
            gate={"run": f'"{sys.executable}" "{script}"'},
        )
        runner = _StubRunner(write_done_on_call=99)  # never green; one fix attempt
        GatedSessionExecutor(max_fix_attempts=1).run_trial(task, ws, None, runner)
        fix_prompts = [p for p in runner.prompts if "quality gate is failing" in p]
        assert fix_prompts, "the gate stayed red, so a fix must have been briefed"
        assert "FAILED on 2 checks" in fix_prompts[0], fix_prompts[0]


# ---------------------------------------------------------------------------
# Blindness: what a gate hands the fix spawn.
#
# A gate runs code the agent wrote (its tests, its conftest, the package a probe
# imports), and whatever the gate prints goes back to the agent in the fix prompt.
# So neither the gate's environment nor the prompt may carry fathom's own state:
# FATHOM_STREAM_TAG names the arm, FATHOM_STREAM_DIR and the launch directory name
# the data root, and an expanded `${task_dir}` is a path inside the data root.
# ---------------------------------------------------------------------------

_ARM = "planted-arm-name"


@contextlib.contextmanager
def _harness_env(data_root: Path):
    """The variables a parent `fathom run` holds while a trial's gate runs."""
    planted = {
        "FATHOM_STREAM_TAG": f"bank-x--{_ARM}--t--r0",
        "FATHOM_STREAM_DIR": str(data_root / ".fathom" / "streams" / "bank-x"),
        "PWD": str(data_root),
        "OLDPWD": str(data_root),
    }
    saved = {k: os.environ.get(k) for k in planted}
    os.environ.update(planted)
    try:
        yield planted
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# Prints every harness variable it can see, then fails so the output is re-briefed.
_ENV_DUMP = (
    "import os, sys\n"
    "for k in ('FATHOM_STREAM_TAG', 'FATHOM_STREAM_DIR', 'PWD', 'OLDPWD'):\n"
    "    print(k, '=', os.environ.get(k))\n"
    "print('PATH kept:', bool(os.environ.get('PATH')))\n"
    "sys.exit(1)\n"
)

# A harness-side probe that fails the way a real one does: its traceback names it.
_PATH_DUMP = (
    "import os, sys\n"
    "print('probe at', __file__)\n"
    "print('probe at', os.path.abspath(__file__))\n"
    "print('probe dir', os.path.dirname(os.path.abspath(__file__)))\n"
    "sys.exit(1)\n"
)


def _spellings(path: Path) -> set[str]:
    """Every way a prompt could spell *path*: as given and resolved, native and posix."""
    forms = {str(path), path.as_posix(), str(path.resolve()), path.resolve().as_posix()}
    return forms | {f.lower() for f in forms}


def _data_root_task(root: Path) -> Path:
    task_dir = root / "data-root" / "tasks" / "bank-x" / "task-y"
    task_dir.mkdir(parents=True)
    return task_dir


def test_a_gate_runs_without_the_harness_variables():
    """Agent-written code under the gate must not see the arm name or the data root."""
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _data_root_task(Path(td))
        ws = Path(wd)
        data_root = task_dir.parents[2]
        (ws / "gate.py").write_text(_ENV_DUMP, encoding="utf-8")
        task = Task(
            id="t",
            instruction="x",
            limits={},
            verify={"entry": "verify.py"},
            task_dir=task_dir,
            gate={"run": f'"{sys.executable}" gate.py'},
        )
        runner = _StubRunner(write_done_on_call=99)
        with _harness_env(data_root):
            GatedSessionExecutor(max_fix_attempts=1).run_trial(task, ws, None, runner)
    fix_prompts = [p for p in runner.prompts if "quality gate is failing" in p]
    assert fix_prompts, "the gate stayed red, so a fix must have been briefed"
    prompt = fix_prompts[0]
    assert "PATH kept: True" in prompt, prompt
    assert _ARM not in prompt, prompt
    for spelling in _spellings(data_root):
        assert spelling not in prompt.lower(), prompt


def test_the_fix_prompt_names_neither_the_data_root_nor_the_arm():
    """A `${task_dir}` probe is quoted as written, and its own paths are masked."""
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _data_root_task(Path(td))
        ws = Path(wd)
        data_root = task_dir.parents[2]
        (task_dir / "probe.py").write_text(_PATH_DUMP, encoding="utf-8")
        template = f'"{sys.executable}" "${{task_dir}}/probe.py" "${{workspace}}"'
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=task_dir)
        runner = _StubRunner(write_done_on_call=99)
        ex = GatedSessionExecutor(max_fix_attempts=1, extra_gate_cmds=[template])
        with _harness_env(data_root):
            res = ex.run_trial(task, ws, None, runner)
    fix_prompts = [p for p in runner.prompts if "quality gate is failing" in p]
    assert fix_prompts, "the probe stayed red, so a fix must have been briefed"
    prompt = fix_prompts[0]
    # The probe ran (its output is there) and the command is shown as written.
    assert "probe at" in prompt, prompt
    assert "${task_dir}/probe.py" in prompt, prompt
    assert _ARM not in prompt, prompt
    for spelling in _spellings(data_root):
        assert spelling not in prompt.lower(), prompt
        # The trial row keeps the same masked excerpt.
        assert spelling not in res.detail.lower(), res.detail


def test_masking_covers_every_spelling_of_the_task_dir():
    """As given or resolved, either separator: each becomes the placeholder."""
    with tempfile.TemporaryDirectory() as td:
        task_dir = _data_root_task(Path(td))
        native = str(task_dir.resolve())
        lines = [
            str(task_dir),
            task_dir.as_posix() + "/probe.py",
            native.replace("\\", "/"),
            native + os.sep + "x.py",
        ]
        masked = mask_task_dir("\n".join(lines), task_dir)
    assert masked.count("${task_dir}") == len(lines), masked
    assert "${task_dir}/probe.py" in masked, masked
    for spelling in _spellings(task_dir):
        assert spelling not in masked.lower(), masked


def test_masking_a_filesystem_root_changes_nothing():
    """A root would match every separator; it names no data root, so it is not masked."""
    text = "tests/test_a.py::test_b FAILED at C:/x and /y"
    assert mask_task_dir(text, Path("/")) == text


def test_masking_covers_the_msys_and_the_file_uri_spellings():
    """Git Bash tools print /c/...; a file URI percent-encodes a space."""
    with tempfile.TemporaryDirectory() as td:
        task_dir = Path(td) / "data root" / "tasks" / "bank-x" / "task-y"
        task_dir.mkdir(parents=True)
        uri = task_dir.resolve().as_uri() + "/probe.py"
        lines = [uri]
        posix = task_dir.resolve().as_posix()
        if posix[1:3] == ":/":
            lines.append(f"/{posix[0].lower()}/{posix[3:]}/probe.py")
            lines.append(f"/cygdrive/{posix[0].lower()}/{posix[3:]}/probe.py")
        masked = mask_task_dir("\n".join(lines), task_dir)
    assert masked.count("${task_dir}/probe.py") == len(lines), masked
    assert "data%20root" not in masked and "data root" not in masked, masked


def test_masking_covers_the_head_an_unquoted_command_splits_off():
    """`python C:/x/my evals/...` splits at the space; the head names the data root's
    parent and the start of its name."""
    with tempfile.TemporaryDirectory() as td:
        task_dir = Path(td) / "my evals" / "tasks" / "bank-x" / "task-y"
        task_dir.mkdir(parents=True)
        head = str(Path(td).resolve() / "my")
        text = f"can't open file '{head}': [Errno 2] No such file or directory"
        masked = mask_task_dir(text, task_dir)
        # A longer name that merely starts the same way is a different path.
        other = str(Path(td).resolve() / "mystery.txt")
        assert mask_task_dir(other, task_dir) == other
    assert head not in masked and head.replace("\\", "/") not in masked, masked
    assert "${task_dir}" in masked, masked


# --- placeholders are one shell word, quoted or not ----------------------------------


def _spaced_task(root: Path) -> Path:
    task_dir = root / "my evals" / "tasks" / "bank-x" / "task-y"
    task_dir.mkdir(parents=True)
    return task_dir


def test_an_unquoted_placeholder_survives_a_space_in_the_path():
    """The authoring guide's unquoted form runs the probe when the data root's path
    holds a space, and when the workspace's does."""
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _spaced_task(Path(td))
        ws = Path(wd) / "work space"
        ws.mkdir()
        (task_dir / "probe.py").write_text(_PROBE, encoding="utf-8")
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=task_dir)
        runner = _StubRunner(write_done_on_call=99, files_by_call={1: "ok"})
        template = f'"{sys.executable}" ${{task_dir}}/probe.py ${{workspace}}'
        res = GatedSessionExecutor(max_fix_attempts=0, extra_gate_cmds=[template]).run_trial(
            task, ws, None, runner
        )
    assert "first=green" in res.detail, res.detail


def test_a_quoted_placeholder_is_not_quoted_twice():
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _spaced_task(Path(td))
        (task_dir / "probe.py").write_text(_PROBE, encoding="utf-8")
        cmd = expand_gate_placeholders(
            '"${task_dir}/probe.py"', task_dir=task_dir, workspace=Path(wd)
        )
    assert cmd.count('"') == 2, cmd


def test_a_single_quoted_placeholder_stays_one_word_on_posix():
    if os.name == "nt":
        return  # cmd.exe has no single quotes
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _spaced_task(Path(td))
        (task_dir / "probe.py").write_text(_PROBE, encoding="utf-8")
        (Path(wd) / "ok").write_text("ok", encoding="utf-8")
        cmd = expand_gate_placeholders(
            f"'{sys.executable}' '${{task_dir}}/probe.py' '${{workspace}}'",
            task_dir=task_dir,
            workspace=Path(wd),
        )
        ok, output = GatedSessionExecutor._run_gate(cmd, Path(wd))
    assert ok, output


def test_a_red_gate_names_no_part_of_the_data_roots_location():
    """With a space in the data root's path, a failing probe's fix prompt still names
    nothing above `${task_dir}`: not the data root, and not its parent directory."""
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _spaced_task(Path(td))
        data_root = task_dir.parents[2]
        ws = Path(wd)
        (task_dir / "probe.py").write_text(_PATH_DUMP, encoding="utf-8")
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=task_dir)
        runner = _StubRunner(write_done_on_call=99)
        template = f'"{sys.executable}" ${{task_dir}}/probe.py ${{workspace}}'
        ex = GatedSessionExecutor(max_fix_attempts=1, extra_gate_cmds=[template])
        with hidden_from_children(data_root):
            res = ex.run_trial(task, ws, None, runner)
    fix_prompts = [p for p in runner.prompts if "quality gate is failing" in p]
    assert fix_prompts, "the probe stayed red, so a fix must have been briefed"
    prompt = fix_prompts[0]
    assert "probe at ${task_dir}" in prompt, prompt
    for path in (data_root, data_root.parent):
        for spelling in _spellings(path):
            assert spelling not in prompt.lower(), prompt
            assert spelling not in res.detail.lower(), res.detail


def test_the_gate_command_line_is_masked_too():
    """A template that spells the task directory out, instead of using the placeholder,
    is shown to the agent with the placeholder."""
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _data_root_task(Path(td))
        (task_dir / "probe.py").write_text(_PATH_DUMP, encoding="utf-8")
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=task_dir)
        runner = _StubRunner(write_done_on_call=99)
        spelled_out = f'"{sys.executable}" "{task_dir.resolve().as_posix()}/probe.py"'
        GatedSessionExecutor(max_fix_attempts=1, extra_gate_cmds=[spelled_out]).run_trial(
            task, Path(wd), None, runner
        )
    prompt = next(p for p in runner.prompts if "quality gate is failing" in p)
    command_line = next(line for line in prompt.splitlines() if line.startswith("Gate command:"))
    assert '"${task_dir}/probe.py"' in command_line, command_line
    for spelling in _spellings(task_dir):
        assert spelling not in prompt.lower(), prompt


def test_other_paths_in_the_data_root_are_withheld_from_the_output():
    """A probe that walks up from its own file names the data root; masked as withheld."""
    walker = (
        "import os, sys\n"
        "root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n"
        "print('bank root', os.path.dirname(root))\n"
        "sys.exit(1)\n"
    )
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _data_root_task(Path(td))
        data_root = task_dir.parents[2]
        (task_dir / "probe.py").write_text(walker, encoding="utf-8")
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=task_dir)
        runner = _StubRunner(write_done_on_call=99)
        template = f'"{sys.executable}" "${{task_dir}}/probe.py"'
        ex = GatedSessionExecutor(max_fix_attempts=1, extra_gate_cmds=[template])
        with hidden_from_children(data_root):
            ex.run_trial(task, Path(wd), None, runner)
    prompt = next(p for p in runner.prompts if "quality gate is failing" in p)
    assert f"bank root {MASKED_DIR}" in prompt, prompt
    for spelling in _spellings(data_root):
        assert spelling not in prompt.lower(), prompt


def test_masking_covers_paths_relative_to_the_workspace():
    """A gate runs in the workspace, and a tool that prints the shorter of the relative
    and the absolute spelling (pytest does) names the data root as `..\\..\\<root>\\...`.
    The agent knows its own directory, so that line locates the data root."""
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _data_root_task(Path(td))
        data_root = task_dir.parents[2]
        ws = Path(wd)
        rel = os.path.relpath(task_dir, ws)
        back = rel.replace("/", "\\")
        fwd = rel.replace("\\", "/")
        other = os.path.relpath(data_root / "notes.txt", ws).replace("\\", "/")
        lines = [
            f"{back}\\probe.py:6: AssertionError",
            f"FAILED {back}\\test_x.py::test",
            f"FAILED {fwd}/test_x.py::test",
            # From a directory one level down in the workspace (a gate that `cd`s first).
            f"../{fwd}/probe.py",
            other,
        ]
        with hidden_from_children(data_root):
            masked = mask_gate_text("\n".join(lines), task_dir, workspace=ws)
    assert masked.splitlines() == [
        "${task_dir}\\probe.py:6: AssertionError",
        "FAILED ${task_dir}\\test_x.py::test",
        "FAILED ${task_dir}/test_x.py::test",
        "${task_dir}/probe.py",
        f"{MASKED_DIR}/notes.txt",
    ], masked
    for name in (Path(td).name, data_root.name, "bank-x", "task-y"):
        assert name.lower() not in masked.lower(), masked


def test_a_relative_path_inside_the_workspace_is_left_alone():
    """Only a path that climbs out of the workspace can name the data root."""
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _data_root_task(Path(td))
        text = "FAILED tests/test_calc.py::test_add - ../x/y.py and .."
        assert mask_gate_text(text, task_dir, workspace=Path(wd)) == text


def test_a_red_pytest_gate_names_no_part_of_the_data_root():
    """End to end: pytest runs a hidden test from `${task_dir}` in the workspace, and
    reports its location relative to the workspace when that is shorter."""
    import importlib.util

    if importlib.util.find_spec("pytest") is None:
        return  # run without the dev tools (`python tests/test_gated_session.py`)
    hidden_test = "def test_add():\n    assert 1 + 1 == 3\n"
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        task_dir = _data_root_task(Path(td))
        data_root = task_dir.parents[2]
        (task_dir / "test_hidden.py").write_text(hidden_test, encoding="utf-8")
        task = Task(id="t", instruction="x", limits={}, verify={"entry": "v.py"}, task_dir=task_dir)
        runner = _StubRunner(write_done_on_call=99)
        template = (
            f'"{sys.executable}" -m pytest -q -p no:cacheprovider ${{task_dir}}/test_hidden.py'
        )
        ex = GatedSessionExecutor(max_fix_attempts=1, extra_gate_cmds=[template])
        with hidden_from_children(data_root):
            res = ex.run_trial(task, Path(wd), None, runner)
    prompt = next(p for p in runner.prompts if "quality gate is failing" in p)
    assert "test_hidden.py" in prompt, prompt  # pytest ran and reported the failure
    for name in (Path(td).name, data_root.name, "bank-x", "task-y"):
        assert name.lower() not in prompt.lower(), prompt
        assert name.lower() not in res.detail.lower(), res.detail


def test_masking_covers_the_short_name_of_the_task_dir():
    """Windows can name a directory by its 8.3 short name, which shares no text with
    the long one past the first differing component."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    get_short = ctypes.WinDLL("kernel32").GetShortPathNameW
    get_short.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    get_short.restype = wintypes.DWORD
    with tempfile.TemporaryDirectory() as td:
        task_dir = Path(td) / "a-long-data-root" / "tasks" / "a-long-bank" / "a-long-task"
        task_dir.mkdir(parents=True)
        buf = ctypes.create_unicode_buffer(1024)
        if not get_short(str(task_dir), buf, 1024) or buf.value == str(task_dir):
            return  # short names are off on this volume
        short = buf.value
        masked = mask_task_dir(short + "\\probe.py", task_dir)
    assert masked == "${task_dir}\\probe.py", masked


def test_a_gate_that_outlives_its_timeout_is_stopped_with_its_children():
    """The gate's timeout stops the whole process tree, promptly: a shell whose child
    sleeps must neither hold the matrix until the child is done nor leave the child to
    write into the scored workspace after the gate returned."""
    import time

    from fathom.strategies import gated_session as gs

    late = (
        f'"{sys.executable}" -c "import time, pathlib; time.sleep(5); '
        "pathlib.Path('late.txt').write_text('x')\" && echo done"
    )
    saved = gs._GATE_TIMEOUT_S
    gs._GATE_TIMEOUT_S = 1
    try:
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d)
            start = time.monotonic()
            ok, output = GatedSessionExecutor._run_gate(late, ws)
            elapsed = time.monotonic() - start
            time.sleep(max(0.0, 6.5 - elapsed))
            left = sorted(p.name for p in ws.iterdir())
    finally:
        gs._GATE_TIMEOUT_S = saved
    assert ok is False
    assert "timed out" in output, output
    assert elapsed < 4, f"the gate returned after {elapsed:.1f}s"
    assert left == [], left


def test_the_gate_env_holds_no_billing_or_api_credential():
    """What a gate prints goes back to the agent and into the trial row, and the spawn
    itself never receives these."""
    dump = (
        "import os\n"
        "print('SEEN:', sorted(k for k in os.environ if k.upper() in "
        "{'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'AWS_BEARER_TOKEN_BEDROCK'}))\n"
        "print('KEPT:', os.environ.get('GATE_ENV_TEST_BENIGN'))\n"
    )
    planted = {
        "ANTHROPIC_API_KEY": "planted-key",
        "ANTHROPIC_AUTH_TOKEN": "planted-token",
        "AWS_BEARER_TOKEN_BEDROCK": "planted-bearer",
        "GATE_ENV_TEST_BENIGN": "keep-me",
    }
    saved = {k: os.environ.get(k) for k in planted}
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        (ws / "gate.py").write_text(dump, encoding="utf-8")
        os.environ.update(planted)
        try:
            ok, output = GatedSessionExecutor._run_gate(f'"{sys.executable}" gate.py', ws)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    assert ok, output
    assert "SEEN: []" in output, output
    assert "KEPT: keep-me" in output, output


def test_the_gate_env_withholds_values_naming_the_data_root():
    """VIRTUAL_ENV and PATH name the data root when fathom runs from a venv in it."""
    names_naming = (
        "import os, sys\n"
        "root = sys.argv[1].replace('\\\\', '/').lower()\n"
        "bad = sorted(k for k, v in os.environ.items()\n"
        "             if root in v.replace('\\\\', '/').lower())\n"
        "print('NAMING:', bad)\n"
    )
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
        data_root = Path(td) / "data-root"
        venv_scripts = data_root / ".venv" / ("Scripts" if os.name == "nt" else "bin")
        venv_scripts.mkdir(parents=True)
        ws = Path(wd)
        script = Path(td) / "names.py"
        script.write_text(names_naming, encoding="utf-8")
        planted = {
            "VIRTUAL_ENV": str(data_root / ".venv"),
            "PATH": os.pathsep.join([str(venv_scripts), os.environ.get("PATH", "")]),
        }
        saved = {k: os.environ.get(k) for k in planted}
        os.environ.update(planted)
        try:
            with hidden_from_children(data_root):
                ok, output = GatedSessionExecutor._run_gate(
                    f'"{sys.executable}" "{script}" "{data_root.resolve()}"', ws
                )
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    assert ok, output
    assert "NAMING: []" in output, output


# --- what a gate creates in the scored workspace ---------------------------------------

_CALC = "def add(a, b):\n    return a + b\n"
_TEST_CALC = "from calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"
# A gate that leaves files behind in the workspace, as a test runner or a build does.
_LITTERING_GATE = (
    f'"{sys.executable}" -c "import os; os.makedirs(\'build/cache\', exist_ok=True); '
    "open('build/cache/x', 'w').write('1'); open('gate.log', 'w').write('1'); "
    "open('calc.py', 'a').write('')\""
)


class _CalcAgent:
    """Writes the same two files on its first call, whichever strategy runs it."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def execute(self, prompt, workspace, scenario, max_turns=None):
        self.prompts.append(prompt)
        if len(self.prompts) == 1:
            (Path(workspace) / "calc.py").write_text(_CALC, encoding="utf-8")
            (Path(workspace) / "test_calc.py").write_text(_TEST_CALC, encoding="utf-8")
        return RunRecord(status=ExitStatus.OK, duration_s=1.0, num_turns=1)


def _result_view_files(workspace: Path) -> list[str]:
    with tempfile.TemporaryDirectory() as vd:
        extract_result_view(workspace, Path(vd))
        return sorted(p.relative_to(vd).as_posix() for p in Path(vd).rglob("*"))


def _views_with_and_without(gate: str) -> tuple[list[str], list[str]]:
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        single_ws, gated_ws = Path(a), Path(b)
        task = Task(
            id="t",
            instruction="add",
            limits={},
            verify={"entry": "v.py"},
            task_dir=gated_ws,
            gate={"run": gate},
        )
        SingleSessionExecutor().run_trial(task, single_ws, None, _CalcAgent())
        res = GatedSessionExecutor().run_trial(task, gated_ws, None, _CalcAgent())
        assert "final=green" in res.detail, res.detail
        return _result_view_files(single_ws), _result_view_files(gated_ws)


def test_a_gate_leaves_nothing_in_the_scored_tree():
    single, gated = _views_with_and_without(_LITTERING_GATE)
    assert single == ["calc.py", "test_calc.py"], single
    assert gated == single, gated


def test_a_pytest_gate_leaves_no_cache_in_the_scored_tree():
    single, gated = _views_with_and_without(f'"{sys.executable}" -m pytest -q')
    assert gated == single, gated


def test_files_written_between_gates_stay():
    """Only what a gate itself creates goes: the agent's fix, written after a red gate,
    is scored."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        runner = _StubRunner(write_done_on_call=2, files_by_call={2: "fix.txt"})
        gate = (
            f"\"{sys.executable}\" -c \"open('gate.log', 'w').write('1'); "
            "import os, sys; sys.exit(0 if os.path.exists('done') else 1)\""
        )
        res = GatedSessionExecutor(max_fix_attempts=2).run_trial(
            _task_with(ws, gate), ws, None, runner
        )
        files = sorted(p.name for p in ws.iterdir())
    assert "final=green" in res.detail, res.detail
    assert files == ["done", "fix.txt"], files


def _task_with(ws: Path, gate: str) -> Task:
    return Task(
        id="t",
        instruction="x",
        limits={},
        verify={"entry": "v.py"},
        task_dir=ws,
        gate={"run": gate},
    )


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
        test_undecodable_gate_output_is_not_an_empty_re_brief,
        test_a_lost_gate_stream_is_a_named_condition_not_an_empty_string,
        test_fix_prompt_carries_the_undecodable_output,
        test_a_gate_runs_without_the_harness_variables,
        test_the_fix_prompt_names_neither_the_data_root_nor_the_arm,
        test_masking_covers_every_spelling_of_the_task_dir,
        test_masking_a_filesystem_root_changes_nothing,
        test_masking_covers_the_msys_and_the_file_uri_spellings,
        test_masking_covers_the_head_an_unquoted_command_splits_off,
        test_an_unquoted_placeholder_survives_a_space_in_the_path,
        test_a_quoted_placeholder_is_not_quoted_twice,
        test_a_single_quoted_placeholder_stays_one_word_on_posix,
        test_a_red_gate_names_no_part_of_the_data_roots_location,
        test_the_gate_command_line_is_masked_too,
        test_other_paths_in_the_data_root_are_withheld_from_the_output,
        test_masking_covers_paths_relative_to_the_workspace,
        test_a_relative_path_inside_the_workspace_is_left_alone,
        test_a_red_pytest_gate_names_no_part_of_the_data_root,
        test_masking_covers_the_short_name_of_the_task_dir,
        test_a_gate_that_outlives_its_timeout_is_stopped_with_its_children,
        test_the_gate_env_holds_no_billing_or_api_credential,
        test_the_gate_env_withholds_values_naming_the_data_root,
        test_a_gate_leaves_nothing_in_the_scored_tree,
        test_a_pytest_gate_leaves_no_cache_in_the_scored_tree,
        test_files_written_between_gates_stay,
    ):
        fn()
        print(f"ok {fn.__name__}")
    print("all gated_session tests passed")
