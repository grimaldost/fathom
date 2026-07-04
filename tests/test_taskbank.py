"""Tests for src/fathom/taskbank.py — stdlib-runnable."""

import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

# Allow `python tests/test_taskbank.py` from the project root without PYTHONPATH.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom.taskbank import (
    Bank,
    DuplicateTaskIdError,
    InvalidHoldoutIdError,
    MissingFieldError,
    Task,
    load_bank,
    stage_task,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_BANK = FIXTURES / "sample_bank"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bank_dir(tmp_path: Path, bank_toml: str, tasks: list[tuple[str, str, dict]]) -> Path:
    """Write a minimal bank directory tree for error-case tests."""
    bank_path = tmp_path / "bank"
    bank_path.mkdir()
    (bank_path / "bank.toml").write_text(bank_toml, encoding="utf-8")
    for task_id, task_toml_content, fixture_files in tasks:
        task_dir = bank_path / task_id
        task_dir.mkdir()
        (task_dir / "task.toml").write_text(task_toml_content, encoding="utf-8")
        fixtures_dir = task_dir / "fixtures"
        fixtures_dir.mkdir()
        for name, content in fixture_files.items():
            (fixtures_dir / name).write_text(content, encoding="utf-8")
    return bank_path


VALID_TASK_TOML = """\
id = "task_x"
instruction = "Do something."

[limits]
max_turns = 5

[verify]
entry = "verify.py"
"""

VALID_BANK_TOML = """\
name = "test"
dataset_version = "0.1.0"
holdout = []
"""


# ---------------------------------------------------------------------------
# Bank loading — happy path
# ---------------------------------------------------------------------------


def test_load_bank_name_and_version():
    bank = load_bank(SAMPLE_BANK)
    assert bank.name == "sample"
    assert bank.dataset_version == "1.0.0"


def test_load_bank_tasks_loaded():
    bank = load_bank(SAMPLE_BANK)
    assert len(bank.tasks) == 2
    ids = {t.id for t in bank.tasks}
    assert ids == {"task_a", "task_b"}


def test_load_bank_task_fields():
    bank = load_bank(SAMPLE_BANK)
    task_a = next(t for t in bank.tasks if t.id == "task_a")
    assert "add function" in task_a.instruction
    assert task_a.limits["max_turns"] == 10
    assert task_a.limits["timeout_seconds"] == 300
    assert task_a.verify["entry"] == "verify.py"
    assert task_a.task_dir == SAMPLE_BANK / "task_a"


def test_load_bank_task_returns_task_instances():
    bank = load_bank(SAMPLE_BANK)
    for task in bank.tasks:
        assert isinstance(task, Task)


def test_load_bank_returns_bank_instance():
    bank = load_bank(SAMPLE_BANK)
    assert isinstance(bank, Bank)


# ---------------------------------------------------------------------------
# Holdout parsing and validation
# ---------------------------------------------------------------------------


def test_load_bank_holdout_parsed():
    bank = load_bank(SAMPLE_BANK)
    assert bank.holdout == ["task_b"]


def test_load_bank_empty_holdout():
    with tempfile.TemporaryDirectory() as tmp:
        bank_dir = _make_bank_dir(
            Path(tmp),
            bank_toml=VALID_BANK_TOML,
            tasks=[("task_x", VALID_TASK_TOML, {"placeholder.txt": "hi"})],
        )
        bank = load_bank(bank_dir)
        assert bank.holdout == []


def test_load_bank_invalid_holdout_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bank_dir = _make_bank_dir(
            Path(tmp),
            bank_toml='name = "t"\ndataset_version = "1"\nholdout = ["nonexistent"]\n',
            tasks=[("task_x", VALID_TASK_TOML, {"placeholder.txt": "hi"})],
        )
        try:
            load_bank(bank_dir)
            raise AssertionError("expected InvalidHoldoutIdError")
        except InvalidHoldoutIdError as exc:
            assert "nonexistent" in str(exc)


# ---------------------------------------------------------------------------
# Error cases — named errors on bad inputs
# ---------------------------------------------------------------------------


def test_duplicate_task_id_raises():
    with tempfile.TemporaryDirectory() as tmp:
        dup_task_toml = VALID_TASK_TOML  # id = "task_x" in both
        bank_dir = _make_bank_dir(
            Path(tmp),
            bank_toml=VALID_BANK_TOML,
            tasks=[
                ("dir_a", dup_task_toml, {}),
                ("dir_b", dup_task_toml, {}),
            ],
        )
        try:
            load_bank(bank_dir)
            raise AssertionError("expected DuplicateTaskIdError")
        except DuplicateTaskIdError as exc:
            assert "task_x" in str(exc)


def test_missing_bank_name_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bank_dir = _make_bank_dir(
            Path(tmp),
            bank_toml='dataset_version = "1.0"\nholdout = []\n',
            tasks=[("task_x", VALID_TASK_TOML, {})],
        )
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "name" in str(exc)


def test_missing_bank_dataset_version_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bank_dir = _make_bank_dir(
            Path(tmp),
            bank_toml='name = "t"\nholdout = []\n',
            tasks=[("task_x", VALID_TASK_TOML, {})],
        )
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "dataset_version" in str(exc)


def test_missing_bank_holdout_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bank_dir = _make_bank_dir(
            Path(tmp),
            bank_toml='name = "t"\ndataset_version = "1.0"\n',
            tasks=[("task_x", VALID_TASK_TOML, {})],
        )
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "holdout" in str(exc)


def test_missing_task_id_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bad_task = 'instruction = "x"\n[limits]\n[verify]\nentry = "v.py"\n'
        bank_dir = _make_bank_dir(Path(tmp), bank_toml=VALID_BANK_TOML, tasks=[("t", bad_task, {})])
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "id" in str(exc)


def test_missing_task_instruction_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bad_task = 'id = "t"\n[limits]\n[verify]\nentry = "v.py"\n'
        bank_dir = _make_bank_dir(Path(tmp), bank_toml=VALID_BANK_TOML, tasks=[("t", bad_task, {})])
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "instruction" in str(exc)


def test_missing_task_limits_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bad_task = 'id = "t"\ninstruction = "x"\n[verify]\nentry = "v.py"\n'
        bank_dir = _make_bank_dir(Path(tmp), bank_toml=VALID_BANK_TOML, tasks=[("t", bad_task, {})])
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "limits" in str(exc)


def test_missing_task_verify_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bad_task = 'id = "t"\ninstruction = "x"\n[limits]\n'
        bank_dir = _make_bank_dir(Path(tmp), bank_toml=VALID_BANK_TOML, tasks=[("t", bad_task, {})])
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "verify" in str(exc)


def test_missing_verify_entry_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bad_task = 'id = "t"\ninstruction = "x"\n[limits]\n[verify]\n'
        bank_dir = _make_bank_dir(Path(tmp), bank_toml=VALID_BANK_TOML, tasks=[("t", bad_task, {})])
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "entry" in str(exc)


def test_task_verify_scalar_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bad_task = 'id = "t"\ninstruction = "x"\n[limits]\nverify = "my_entry"\n'
        bank_dir = _make_bank_dir(Path(tmp), bank_toml=VALID_BANK_TOML, tasks=[("t", bad_task, {})])
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "verify" in str(exc)


def test_task_limits_scalar_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bad_task = 'id = "t"\ninstruction = "x"\nlimits = 5\n[verify]\nentry = "v.py"\n'
        bank_dir = _make_bank_dir(Path(tmp), bank_toml=VALID_BANK_TOML, tasks=[("t", bad_task, {})])
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "limits" in str(exc)


def test_bank_holdout_scalar_raises():
    with tempfile.TemporaryDirectory() as tmp:
        bank_dir = _make_bank_dir(
            Path(tmp),
            bank_toml='name = "t"\ndataset_version = "1"\nholdout = "task_x"\n',
            tasks=[("task_x", VALID_TASK_TOML, {})],
        )
        try:
            load_bank(bank_dir)
            raise AssertionError("expected MissingFieldError")
        except MissingFieldError as exc:
            assert "holdout" in str(exc)


# ---------------------------------------------------------------------------
# Staging
# ---------------------------------------------------------------------------


def test_stage_task_is_git_repo():
    bank = load_bank(SAMPLE_BANK)
    task_a = next(t for t in bank.tasks if t.id == "task_a")
    with stage_task(task_a, "main") as workspace:
        assert (workspace / ".git").is_dir()


def test_stage_task_pinned_branch():
    bank = load_bank(SAMPLE_BANK)
    task_a = next(t for t in bank.tasks if t.id == "task_a")
    with stage_task(task_a, "feat-base") as workspace:
        result = subprocess.run(
            ["git", "-C", str(workspace), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feat-base"


def test_stage_task_autocrlf_false():
    bank = load_bank(SAMPLE_BANK)
    task_a = next(t for t in bank.tasks if t.id == "task_a")
    with stage_task(task_a, "main") as workspace:
        result = subprocess.run(
            ["git", "-C", str(workspace), "config", "core.autocrlf"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "false"


def test_stage_task_fixture_content_committed():
    bank = load_bank(SAMPLE_BANK)
    task_a = next(t for t in bank.tasks if t.id == "task_a")
    with stage_task(task_a, "main") as workspace:
        # file exists in workspace
        assert (workspace / "main.py").exists()
        # there is at least one commit
        result = subprocess.run(
            ["git", "-C", str(workspace), "log", "--oneline"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() != ""
        # main.py is tracked (not untracked)
        status = subprocess.run(
            ["git", "-C", str(workspace), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert status.stdout.strip() == ""
        # main.py actually appears in the commit tree (not just the working tree)
        tree = subprocess.run(
            ["git", "-C", str(workspace), "ls-tree", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "main.py" in tree.stdout


def test_stage_task_workspace_cleaned_up():
    bank = load_bank(SAMPLE_BANK)
    task_a = next(t for t in bank.tasks if t.id == "task_a")
    workspace_path = None
    with stage_task(task_a, "main") as workspace:
        workspace_path = workspace
        assert workspace_path.exists()
    assert not workspace_path.exists()


def test_stage_task_no_fixtures_dir():
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp) / "no_fixtures_task"
        task_dir.mkdir()
        task = Task(
            id="no_fixtures",
            instruction="x",
            limits={},
            verify={"entry": "v.py"},
            task_dir=task_dir,
        )
        with stage_task(task, "main") as workspace:
            assert (workspace / ".git").is_dir()
            result = subprocess.run(
                ["git", "-C", str(workspace), "log", "--oneline"],
                capture_output=True,
                text=True,
                check=True,
            )
            assert result.stdout.strip() != ""


def test_stage_task_cleanup_on_exception():
    bank = load_bank(SAMPLE_BANK)
    task_a = next(t for t in bank.tasks if t.id == "task_a")
    workspace_path = None
    try:
        with stage_task(task_a, "main") as workspace:
            workspace_path = workspace
            raise RuntimeError("simulated failure")
    except RuntimeError:
        pass
    assert workspace_path is not None
    assert not workspace_path.exists()


# ---------------------------------------------------------------------------
# stdlib runner
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    tests = [
        test_load_bank_name_and_version,
        test_load_bank_tasks_loaded,
        test_load_bank_task_fields,
        test_load_bank_task_returns_task_instances,
        test_load_bank_returns_bank_instance,
        test_load_bank_holdout_parsed,
        test_load_bank_empty_holdout,
        test_load_bank_invalid_holdout_raises,
        test_duplicate_task_id_raises,
        test_missing_bank_name_raises,
        test_missing_bank_dataset_version_raises,
        test_missing_bank_holdout_raises,
        test_missing_task_id_raises,
        test_missing_task_instruction_raises,
        test_missing_task_limits_raises,
        test_missing_task_verify_raises,
        test_missing_verify_entry_raises,
        test_task_verify_scalar_raises,
        test_task_limits_scalar_raises,
        test_bank_holdout_scalar_raises,
        test_stage_task_is_git_repo,
        test_stage_task_pinned_branch,
        test_stage_task_autocrlf_false,
        test_stage_task_fixture_content_committed,
        test_stage_task_workspace_cleaned_up,
        test_stage_task_no_fixtures_dir,
        test_stage_task_cleanup_on_exception,
    ]

    failures = []
    for test_fn in tests:
        try:
            test_fn()
        except Exception:
            failures.append(test_fn.__name__)
            traceback.print_exc()
            print()

    if failures:
        print(f"FAILED: {len(failures)}/{len(tests)} — {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"All {len(tests)} tests passed!")
