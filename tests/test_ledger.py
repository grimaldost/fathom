"""Tests for fathom.ledger — stdlib-runnable.

Run via pytest or directly:  python tests/test_ledger.py
"""

import dataclasses
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
    VoidRecord,
    append_record,
    apply_voids,
    completed_keys,
    iter_records,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_trial(**kwargs) -> TrialRecord:
    defaults: dict = {
        "bank": "test-bank",
        "task_id": "task-001",
        "repeat": 0,
        "status": "completed",
        "dataset_version": "v1",
        "config_hash": "abc123",
        "tool_git_sha": "def456",
        "cli_version": "1.0.0",
        "pin_level": "strong",
    }
    defaults.update(kwargs)
    return TrialRecord(**defaults)


def make_run(**kwargs) -> RunRecord:
    defaults: dict = {
        "bank": "test-bank",
        "task_id": "task-001",
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
    defaults.update(kwargs)
    return RunRecord(**defaults)


def make_grading(**kwargs) -> GradingRecord:
    defaults: dict = {
        "bank": "test-bank",
        "task_id": "task-001",
        "repeat": 0,
        "verdict": "a",
        "dataset_version": "v1",
        "config_hash_a": "abc123",
        "config_hash_b": "xyz789",
        "tool_git_sha": "def456",
        "cli_version": "1.0.0",
        "judge_config_hash": "jdg000",
        "judge_model": "claude-sonnet-4-6",
        "pin_level": "strong",
    }
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
    """The adapter-computed USD estimate survives the ledger round-trip."""
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


def test_appended_lines_are_lf_on_every_platform():
    """The ledger is a hashed artifact, so its line endings are part of its identity.

    `.gitattributes` pins `*.jsonl text eol=lf` and the ledger index stamps each file by
    digest. Appending through Python text mode wrote CRLF on Windows: git normalised it
    away on check-in, so the committed bytes stayed LF and nothing looked wrong in a
    diff — while the working tree hashed differently from every other platform.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("bank-eol", make_trial(bank="bank-eol", task_id="t-1"), ledger_dir=d)
        append_record("bank-eol", make_trial(bank="bank-eol", task_id="t-2"), ledger_dir=d)

        raw = (d / "bank-eol.jsonl").read_bytes()

        assert b"\r" not in raw, (
            "ledger written with CR bytes; the digest is now platform-dependent"
        )
        assert raw.count(b"\n") == 2, "expected one LF per appended record"


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
        test_appended_lines_are_lf_on_every_platform,
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


# ---------------------------------------------------------------------------
# Void rows: append-only exclusion, order-aware
# ---------------------------------------------------------------------------


def _void_for(trial: TrialRecord, reason: str = "fixture drift") -> VoidRecord:
    return VoidRecord(
        bank=trial.bank,
        task_id=trial.task_id,
        repeat=trial.repeat,
        dataset_version=trial.dataset_version,
        config_hash=trial.config_hash,
        scenario="arm",
        reason=reason,
        evidence="streams/x.ndjson",
        voided_at="2026-01-01T00:00:00+00:00",
    )


def test_void_round_trips_and_keeps_its_kind():
    with tempfile.TemporaryDirectory() as tmp:
        ledger_dir = pathlib.Path(tmp)
        trial = make_trial(repeat=3)
        append_record("test-bank", trial, ledger_dir=ledger_dir)
        append_record("test-bank", _void_for(trial), ledger_dir=ledger_dir)
        records = list(iter_records("test-bank", ledger_dir=ledger_dir))
        assert isinstance(records[-1], VoidRecord)
        assert records[-1].kind == "void"
        assert records[-1].reason == "fixture drift"


def test_a_void_removes_the_key_from_the_resume_set_until_it_is_rerun():
    with tempfile.TemporaryDirectory() as tmp:
        ledger_dir = pathlib.Path(tmp)
        trial = make_trial(repeat=3)
        key = (trial.bank, trial.dataset_version, trial.task_id, trial.config_hash, trial.repeat)
        append_record("test-bank", trial, ledger_dir=ledger_dir)
        assert key in completed_keys("test-bank", ledger_dir=ledger_dir)
        append_record("test-bank", _void_for(trial), ledger_dir=ledger_dir)
        assert key not in completed_keys("test-bank", ledger_dir=ledger_dir)
        # The re-run, appended after the void, counts again.
        append_record("test-bank", make_trial(repeat=3), ledger_dir=ledger_dir)
        assert key in completed_keys("test-bank", ledger_dir=ledger_dir)


def test_apply_voids_drops_earlier_trial_and_run_rows_only():
    base = {
        "bank": "b",
        "dataset_version": "v1",
        "task_id": "t",
        "config_hash": "c" * 64,
        "repeat": 2,
    }
    earlier_trial = {"kind": "trial", "status": "completed", **base}
    earlier_run = {"kind": "run", "cost_usd_est": 1.0, **base}
    other = {"kind": "trial", "status": "completed", **{**base, "repeat": 5}}
    void = {"kind": "void", "reason": "r", **base}
    rerun_trial = {"kind": "trial", "status": "completed", **base}
    rerun_run = {"kind": "run", "cost_usd_est": 2.0, **base}
    kept = apply_voids([earlier_run, earlier_trial, other, void, rerun_run, rerun_trial])
    assert kept == [other, void, rerun_run, rerun_trial]


def test_apply_voids_without_voids_is_identity():
    rows = [{"kind": "trial", "status": "completed", "bank": "b", "repeat": 0}]
    assert apply_voids(rows) == rows


# ---------------------------------------------------------------------------
# engine_version: provenance on every appended row, invisible to every reader
# ---------------------------------------------------------------------------


def test_every_appended_row_records_the_engine_version():
    from fathom.ledger import engine_version

    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("bank", make_trial(), ledger_dir=d)
        append_record("bank", make_run(), ledger_dir=d)
        append_record("bank", {"kind": "future-kind", "x": 1}, ledger_dir=d)
        rows = [json.loads(line) for line in (d / "bank.jsonl").read_text("utf-8").splitlines()]
        assert [r["engine_version"] for r in rows] == [engine_version()] * 3
        assert engine_version(), "never an empty string"


def test_an_explicit_engine_version_is_kept():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        append_record("bank", {"kind": "trial", "engine_version": "0.1.0"}, ledger_dir=d)
        row = json.loads((d / "bank.jsonl").read_text("utf-8"))
        assert row["engine_version"] == "0.1.0"


def test_rows_with_and_without_engine_version_read_the_same():
    """Old rows carry no engine_version; the dataclass view and the resume key ignore it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = pathlib.Path(tmpdir)
        trial = make_trial()
        plain = json.dumps({**trial.__dict__, "kind": "trial"}, sort_keys=True)
        stamped = json.dumps({**trial.__dict__, "kind": "trial", "engine_version": "9.9.9"})
        (d / "old.jsonl").write_text(plain + "\n", encoding="utf-8")
        (d / "new.jsonl").write_text(stamped + "\n", encoding="utf-8")
        old = list(iter_records("old", ledger_dir=d))
        new = list(iter_records("new", ledger_dir=d))
        assert old == new == [trial]
        assert completed_keys("old", ledger_dir=d) == completed_keys("new", ledger_dir=d)


def test_engine_version_says_unknown_without_package_metadata():
    from importlib import metadata
    from unittest import mock

    from fathom import ledger as _ledger

    def _absent(name):
        raise metadata.PackageNotFoundError(name)

    _ledger.engine_version.cache_clear()
    try:
        with mock.patch("importlib.metadata.version", _absent):
            assert _ledger.engine_version() == "unknown"
    finally:
        _ledger.engine_version.cache_clear()


# ---------------------------------------------------------------------------
# written_at: write-time provenance on every appended row; scenario on run rows
# ---------------------------------------------------------------------------


def _read_rows(d: pathlib.Path, bank: str = "test-bank") -> list[dict]:
    text = (d / f"{bank}.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_every_appended_row_carries_a_utc_write_time():
    import datetime

    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        trial = make_trial()
        append_record("test-bank", trial, ledger_dir=d)
        append_record("test-bank", make_run(), ledger_dir=d)
        append_record("test-bank", _void_for(trial), ledger_dir=d)
        rows = _read_rows(d)
        assert [r["kind"] for r in rows] == ["trial", "run", "void"]
        for row in rows:
            stamp = datetime.datetime.fromisoformat(row["written_at"])
            assert stamp.utcoffset() == datetime.timedelta(0), row["kind"]


def test_the_write_time_comes_from_the_clock_seam():
    from unittest import mock

    from fathom import ledger as _ledger

    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        with mock.patch.object(_ledger, "_utc_now", lambda: "2026-01-02T03:04:05+00:00"):
            append_record("test-bank", make_trial(), ledger_dir=d)
        assert _read_rows(d)[0]["written_at"] == "2026-01-02T03:04:05+00:00"


def test_an_explicit_written_at_is_kept():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        row = {**dataclasses.asdict(make_trial()), "written_at": "2020-05-06T07:08:09+00:00"}
        append_record("test-bank", row, ledger_dir=d)
        assert _read_rows(d)[0]["written_at"] == "2020-05-06T07:08:09+00:00"


def test_the_write_time_is_not_a_record_field():
    trial = make_trial()
    assert "written_at" not in {f.name for f in dataclasses.fields(TrialRecord)}
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        append_record("test-bank", trial, ledger_dir=d)
        assert list(iter_records("test-bank", ledger_dir=d)) == [trial]


def test_a_legacy_line_without_write_time_or_scenario_still_loads():
    """No old line is rewritten: a run row from before both fields loads, and the resume
    set built from a ledger with and without written_at is the same."""
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        trial = make_trial()
        run = make_run()
        legacy_run = {
            k: v
            for k, v in dataclasses.asdict(run).items()
            if k not in ("scenario", "cost_usd_est")
        }
        legacy_trial = dataclasses.asdict(trial)
        assert "written_at" not in legacy_run and "scenario" not in legacy_run
        path = d / "test-bank.jsonl"
        path.write_text(
            json.dumps(legacy_run, sort_keys=True) + "\n" + json.dumps(legacy_trial) + "\n",
            encoding="utf-8",
        )
        before = completed_keys("test-bank", ledger_dir=d)
        records = list(iter_records("test-bank", ledger_dir=d))
        assert isinstance(records[0], RunRecord) and records[0].scenario == ""
        assert records[1] == trial
        # A new row appended beside the legacy ones changes nothing about the old keys.
        append_record("test-bank", make_trial(task_id="task-002"), ledger_dir=d)
        assert completed_keys("test-bank", ledger_dir=d) == before | {
            ("test-bank", "v1", "task-002", "abc123", 0)
        }


def test_a_run_record_built_without_scenario_defaults_to_empty():
    assert make_run().scenario == ""


def test_a_run_rows_models_seen_round_trips():
    models = ["claude-opus-4-8-20260115", "claude-haiku-4-5-20251001"]
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        append_record("test-bank", make_run(models_seen=models), ledger_dir=d)
        assert _read_rows(d)[0]["models_seen"] == models
        (record,) = iter_records("test-bank", ledger_dir=d)
        assert isinstance(record, RunRecord) and record.models_seen == models


def test_a_legacy_run_line_without_models_seen_loads_with_an_empty_list():
    """Additive (ADR-0002): a run row from before the field loads unchanged, as []."""
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        legacy = dataclasses.asdict(make_run(model_id="claude-opus-4-8-20260115"))
        legacy.pop("models_seen", None)
        (d / "test-bank.jsonl").write_text(json.dumps(legacy) + "\n", encoding="utf-8")
        (record,) = iter_records("test-bank", ledger_dir=d)
        assert isinstance(record, RunRecord)
        assert record.models_seen == []
        assert record.model_id == "claude-opus-4-8-20260115"


def test_a_run_rows_scenario_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        append_record("test-bank", make_run(scenario="bare"), ledger_dir=d)
        assert _read_rows(d)[0]["scenario"] == "bare"
        (record,) = iter_records("test-bank", ledger_dir=d)
        assert isinstance(record, RunRecord) and record.scenario == "bare"


# ---------------------------------------------------------------------------
# Ledger contract validation: docs/ledger-contract.md field coverage
# ---------------------------------------------------------------------------


def test_every_trial_record_field_appears_in_ledger_contract():
    """Every dataclass field in TrialRecord must be documented in docs/ledger-contract.md."""
    import pathlib as _pathlib

    contract_path = _pathlib.Path(__file__).parent.parent / "docs" / "ledger-contract.md"
    if not contract_path.exists():
        raise FileNotFoundError(f"docs/ledger-contract.md not found at {contract_path}")
    contract_text = contract_path.read_text(encoding="utf-8")

    # Collect all field names from TrialRecord dataclass
    trial_fields = {f.name for f in dataclasses.fields(TrialRecord)}
    # Add 'kind' even though it's init=False (still a documented field)
    trial_fields.add("kind")

    missing_fields = []
    for field_name in sorted(trial_fields):
        # Each field should appear in backticks in the contract
        if f"`{field_name}`" not in contract_text:
            missing_fields.append(field_name)

    assert not missing_fields, f"Trial fields missing from ledger-contract.md: {missing_fields}"


def test_every_run_record_field_appears_in_ledger_contract():
    """Every dataclass field in RunRecord must be documented in docs/ledger-contract.md."""
    import pathlib as _pathlib

    contract_path = _pathlib.Path(__file__).parent.parent / "docs" / "ledger-contract.md"
    if not contract_path.exists():
        raise FileNotFoundError(f"docs/ledger-contract.md not found at {contract_path}")
    contract_text = contract_path.read_text(encoding="utf-8")

    # Collect all field names from RunRecord dataclass
    run_fields = {f.name for f in dataclasses.fields(RunRecord)}
    # Add 'kind' even though it's init=False
    run_fields.add("kind")

    missing_fields = []
    for field_name in sorted(run_fields):
        # Each field should appear in backticks in the contract
        if f"`{field_name}`" not in contract_text:
            missing_fields.append(field_name)

    assert not missing_fields, f"Run fields missing from ledger-contract.md: {missing_fields}"


def test_extra_keys_written_by_trial_loop_appear_in_contract():
    """Extra keys added to trial_dict by cli.py must be documented."""
    import pathlib as _pathlib

    contract_path = _pathlib.Path(__file__).parent.parent / "docs" / "ledger-contract.md"
    contract_text = contract_path.read_text(encoding="utf-8")

    # Keys cli.py adds to trial_dict beyond the dataclass fields
    extra_trial_keys = [
        "valid",
        "verifier_stdout",
        "verifier_stderr",
        "scenario",
        "holdout",
        "fixture_sha",
    ]

    missing_keys = []
    for key_name in extra_trial_keys:
        if f"`{key_name}`" not in contract_text:
            missing_keys.append(key_name)

    assert not missing_keys, f"Extra trial keys missing from ledger-contract.md: {missing_keys}"


# ---------------------------------------------------------------------------
# is_pass rule: the pass-rate decision function
# ---------------------------------------------------------------------------


def test_is_pass_with_none():
    """The pass rule: None gives False."""
    from fathom.report import is_pass

    assert is_pass(None) is False


def test_is_pass_with_empty_dict():
    """The pass rule: empty dict gives False."""
    from fathom.report import is_pass

    assert is_pass({}) is False


def test_is_pass_with_all_truthy_dict():
    """The pass rule: dict with all truthy values gives True."""
    from fathom.report import is_pass

    assert is_pass({"criterion_a": True}) is True
    assert is_pass({"criterion_a": True, "criterion_b": True}) is True
    assert is_pass({"criterion_a": 1, "criterion_b": "yes"}) is True


def test_is_pass_with_any_falsy_dict():
    """The pass rule: dict with any falsy value gives False."""
    from fathom.report import is_pass

    assert is_pass({"criterion_a": False}) is False
    assert is_pass({"criterion_a": True, "criterion_b": False}) is False
    assert is_pass({"criterion_a": 1, "criterion_b": 0}) is False
    assert is_pass({"criterion_a": True, "criterion_b": None}) is False
    assert is_pass({"criterion_a": True, "criterion_b": ""}) is False


def test_is_pass_with_other_types():
    """The pass rule: other types use truthiness."""
    from fathom.report import is_pass

    assert is_pass(True) is True
    assert is_pass(False) is False
    assert is_pass(1) is True
    assert is_pass(0) is False
    assert is_pass("yes") is True
    assert is_pass("") is False
