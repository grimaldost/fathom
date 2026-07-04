"""Tests for fathom.ledger — stdlib-runnable.

Run via pytest or directly:  python tests/test_ledger.py
"""

import json
import pathlib
import sys
import tempfile
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from fathom.ledger import (
    GradingRecord,
    RunRecord,
    TrialRecord,
    append_record,
    completed_keys,
    iter_records,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_trial(**kwargs) -> TrialRecord:
    defaults: dict = dict(
        bank="test-bank",
        task_id="task-001",
        repeat=0,
        status="completed",
        dataset_version="v1",
        config_hash="abc123",
        tool_git_sha="def456",
        cli_version="1.0.0",
        pin_level="strong",
    )
    defaults.update(kwargs)
    return TrialRecord(**defaults)


def make_run(**kwargs) -> RunRecord:
    defaults: dict = dict(
        bank="test-bank",
        task_id="task-001",
        repeat=0,
        usage={"input_tokens": 100, "output_tokens": 50},
        turns=3,
        duration=10.5,
        exit_code=0,
        dataset_version="v1",
        config_hash="abc123",
        tool_git_sha="def456",
        cli_version="1.0.0",
        pin_level="strong",
    )
    defaults.update(kwargs)
    return RunRecord(**defaults)


def make_grading(**kwargs) -> GradingRecord:
    defaults: dict = dict(
        bank="test-bank",
        task_id="task-001",
        repeat=0,
        verdict="a",
        dataset_version="v1",
        config_hash_a="abc123",
        config_hash_b="xyz789",
        tool_git_sha="def456",
        cli_version="1.0.0",
        judge_config_hash="jdg000",
        judge_model="claude-sonnet-4-6",
        pin_level="strong",
    )
    defaults.update(kwargs)
    return GradingRecord(**defaults)


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


def test_trial_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        trial = make_trial(verifier_results={"criterion_a": True, "score": 0.9})
        append_record("test-bank", trial, ledger_dir=d)
        records = list(iter_records("test-bank", ledger_dir=d))
        assert len(records) == 1
        r = records[0]
        assert isinstance(r, TrialRecord)
        assert r.kind == "trial"
        assert r.bank == "test-bank"
        assert r.task_id == "task-001"
        assert r.status == "completed"
        assert r.dataset_version == "v1"
        assert r.config_hash == "abc123"
        assert r.tool_git_sha == "def456"
        assert r.cli_version == "1.0.0"
        assert r.pin_level == "strong"
        assert r.verifier_results == {"criterion_a": True, "score": 0.9}


def test_trial_verifier_results_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        trial = make_trial()
        append_record("test-bank", trial, ledger_dir=d)
        records = list(iter_records("test-bank", ledger_dir=d))
        assert records[0].verifier_results is None


def test_run_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        run = make_run()
        append_record("test-bank", run, ledger_dir=d)
        records = list(iter_records("test-bank", ledger_dir=d))
        assert len(records) == 1
        r = records[0]
        assert isinstance(r, RunRecord)
        assert r.kind == "run"
        assert r.turns == 3
        assert r.duration == 10.5
        assert r.exit_code == 0
        assert r.usage == {"input_tokens": 100, "output_tokens": 50}
        assert r.pin_level == "strong"


def test_run_cost_usd_est_round_trips():
    """The adapter-computed USD estimate survives the ledger round-trip (§11)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("test-bank", make_run(cost_usd_est=0.1234), ledger_dir=d)
        records = list(iter_records("test-bank", ledger_dir=d))
        assert isinstance(records[0], RunRecord)
        assert records[0].cost_usd_est == 0.1234


def test_run_cost_usd_est_defaults_zero_for_legacy_line():
    """Append-only: a pre-existing run line without cost_usd_est still loads,
    defaulting the field to 0.0 (no old line is rewritten)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        # A legacy run record written before the field existed: no cost_usd_est key.
        legacy = {
            "kind": "run",
            "bank": "test-bank",
            "task_id": "t1",
            "repeat": 0,
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "turns": 3,
            "duration": 10.5,
            "exit_code": 0,
            "dataset_version": "v1",
            "config_hash": "abc123",
            "tool_git_sha": "def456",
            "cli_version": "1.0.0",
            "pin_level": "strong",
        }
        path = d / "test-bank.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(legacy, sort_keys=True) + "\n")
        records = list(iter_records("test-bank", ledger_dir=d))
        assert len(records) == 1
        assert isinstance(records[0], RunRecord)
        assert records[0].cost_usd_est == 0.0


def test_grading_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        grading = make_grading()
        append_record("test-bank", grading, ledger_dir=d)
        records = list(iter_records("test-bank", ledger_dir=d))
        assert len(records) == 1
        r = records[0]
        assert isinstance(r, GradingRecord)
        assert r.kind == "grading"
        assert r.verdict == "a"
        assert r.config_hash_a == "abc123"
        assert r.config_hash_b == "xyz789"
        assert r.judge_config_hash == "jdg000"
        assert r.judge_model == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Append-only and ordering
# ---------------------------------------------------------------------------


def test_multiple_appends_preserve_order():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        for i in range(3):
            append_record("test-bank", make_trial(task_id=f"task-{i:03d}"), ledger_dir=d)
        records = list(iter_records("test-bank", ledger_dir=d))
        assert len(records) == 3
        assert [r.task_id for r in records] == ["task-000", "task-001", "task-002"]


def test_mixed_record_kinds_append():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("bank", make_trial(task_id="t1"), ledger_dir=d)
        append_record("bank", make_run(task_id="t1"), ledger_dir=d)
        append_record("bank", make_grading(task_id="t1"), ledger_dir=d)
        records = list(iter_records("bank", ledger_dir=d))
        assert len(records) == 3
        assert isinstance(records[0], TrialRecord)
        assert isinstance(records[1], RunRecord)
        assert isinstance(records[2], GradingRecord)


# ---------------------------------------------------------------------------
# Resume-key computation
# ---------------------------------------------------------------------------


def test_completed_trial_is_in_resume_set():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("test-bank", make_trial(task_id="t1", status="completed"), ledger_dir=d)
        keys = completed_keys("test-bank", ledger_dir=d)
        assert ("test-bank", "v1", "t1", "abc123", 0) in keys


def test_errored_trial_not_in_resume_set():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("test-bank", make_trial(task_id="t1", status="errored"), ledger_dir=d)
        keys = completed_keys("test-bank", ledger_dir=d)
        assert ("test-bank", "v1", "t1", "abc123", 0) not in keys
        assert len(keys) == 0


def test_run_records_do_not_contribute_to_resume_set():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("test-bank", make_run(task_id="t1"), ledger_dir=d)
        keys = completed_keys("test-bank", ledger_dir=d)
        assert len(keys) == 0


def test_grading_records_do_not_contribute_to_resume_set():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("test-bank", make_grading(task_id="t1"), ledger_dir=d)
        keys = completed_keys("test-bank", ledger_dir=d)
        assert len(keys) == 0


def test_resume_set_includes_only_completed():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("test-bank", make_trial(task_id="t1", status="completed"), ledger_dir=d)
        append_record("test-bank", make_trial(task_id="t2", status="errored"), ledger_dir=d)
        append_record("test-bank", make_trial(task_id="t3", status="completed"), ledger_dir=d)
        keys = completed_keys("test-bank", ledger_dir=d)
        assert ("test-bank", "v1", "t1", "abc123", 0) in keys
        assert ("test-bank", "v1", "t2", "abc123", 0) not in keys
        assert ("test-bank", "v1", "t3", "abc123", 0) in keys
        assert len(keys) == 2


def test_resume_key_includes_repeat():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record(
            "test-bank", make_trial(task_id="t1", repeat=0, status="completed"), ledger_dir=d
        )
        append_record(
            "test-bank", make_trial(task_id="t1", repeat=1, status="completed"), ledger_dir=d
        )
        append_record(
            "test-bank", make_trial(task_id="t1", repeat=2, status="errored"), ledger_dir=d
        )
        keys = completed_keys("test-bank", ledger_dir=d)
        assert ("test-bank", "v1", "t1", "abc123", 0) in keys
        assert ("test-bank", "v1", "t1", "abc123", 1) in keys
        assert ("test-bank", "v1", "t1", "abc123", 2) not in keys


# ---------------------------------------------------------------------------
# Tolerant reader
# ---------------------------------------------------------------------------


def test_malformed_line_emits_warning_and_later_lines_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("bank", make_trial(task_id="t1"), ledger_dir=d)
        # Inject malformed line directly
        path = d / "bank.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write("this is not valid json\n")
        append_record("bank", make_trial(task_id="t2"), ledger_dir=d)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            records = list(iter_records("bank", ledger_dir=d))

        assert len(records) == 2
        assert records[0].task_id == "t1"
        assert records[1].task_id == "t2"
        assert len(caught) == 1
        assert "Skipping" in str(caught[0].message)


def test_malformed_line_at_start_still_loads_rest():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        path = d / "bank.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            f.write("{bad json\n")
        append_record("bank", make_trial(task_id="t1"), ledger_dir=d)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            records = list(iter_records("bank", ledger_dir=d))

        assert len(records) == 1
        assert records[0].task_id == "t1"
        assert len(caught) == 1


# ---------------------------------------------------------------------------
# Unknown kinds
# ---------------------------------------------------------------------------


def test_unknown_kind_round_trips_as_dict():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        unknown = {"kind": "future-kind", "payload": "some-value", "version": 99}
        path = d / "bank.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(unknown) + "\n")

        records = list(iter_records("bank", ledger_dir=d))
        assert len(records) == 1
        assert records[0] == unknown


def test_unknown_kind_interleaved_with_known():
    with tempfile.TemporaryDirectory() as templib:
        d = pathlib.Path(templib)
        append_record("bank", make_trial(task_id="t1"), ledger_dir=d)
        path = d / "bank.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": "v2-kind", "x": 1}) + "\n")
        append_record("bank", make_trial(task_id="t2"), ledger_dir=d)

        records = list(iter_records("bank", ledger_dir=d))
        assert len(records) == 3
        assert isinstance(records[0], TrialRecord)
        assert records[1] == {"kind": "v2-kind", "x": 1}
        assert isinstance(records[2], TrialRecord)


# ---------------------------------------------------------------------------
# Per-bank isolation
# ---------------------------------------------------------------------------


def test_per_bank_file_isolation():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("bank-a", make_trial(bank="bank-a", task_id="t-a"), ledger_dir=d)
        append_record("bank-b", make_trial(bank="bank-b", task_id="t-b"), ledger_dir=d)

        records_a = list(iter_records("bank-a", ledger_dir=d))
        records_b = list(iter_records("bank-b", ledger_dir=d))

        assert len(records_a) == 1 and records_a[0].task_id == "t-a"
        assert len(records_b) == 1 and records_b[0].task_id == "t-b"


def test_empty_bank_iter_returns_nothing():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        assert list(iter_records("nonexistent", ledger_dir=d)) == []


def test_empty_bank_completed_keys_returns_empty_set():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        assert completed_keys("nonexistent", ledger_dir=d) == set()


# ---------------------------------------------------------------------------
# Serialization properties
# ---------------------------------------------------------------------------


def test_sort_keys_stable_serialization():
    """The JSONL file uses sort_keys, so field order is deterministic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("bank", make_trial(), ledger_dir=d)
        raw = (d / "bank.jsonl").read_text(encoding="utf-8").strip()
        data = json.loads(raw)
        keys = list(data.keys())
        assert keys == sorted(keys)


def test_series_pin_level_preserved():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("bank", make_trial(pin_level="series"), ledger_dir=d)
        records = list(iter_records("bank", ledger_dir=d))
        assert records[0].pin_level == "series"


# ---------------------------------------------------------------------------
# Stdlib runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_trial_round_trip,
        test_trial_verifier_results_none,
        test_run_round_trip,
        test_run_cost_usd_est_round_trips,
        test_run_cost_usd_est_defaults_zero_for_legacy_line,
        test_grading_round_trip,
        test_multiple_appends_preserve_order,
        test_mixed_record_kinds_append,
        test_completed_trial_is_in_resume_set,
        test_errored_trial_not_in_resume_set,
        test_run_records_do_not_contribute_to_resume_set,
        test_grading_records_do_not_contribute_to_resume_set,
        test_resume_set_includes_only_completed,
        test_resume_key_includes_repeat,
        test_malformed_line_emits_warning_and_later_lines_load,
        test_malformed_line_at_start_still_loads_rest,
        test_unknown_kind_round_trips_as_dict,
        test_unknown_kind_interleaved_with_known,
        test_per_bank_file_isolation,
        test_empty_bank_iter_returns_nothing,
        test_empty_bank_completed_keys_returns_empty_set,
        test_sort_keys_stable_serialization,
        test_series_pin_level_preserved,
    ]
    failed = []
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed.append(t.__name__)
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    if failed:
        sys.exit(1)
