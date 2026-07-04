"""Tests for fathom.report — stdlib-runnable.

Run via pytest or directly:  python tests/test_report.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from fathom.report import render, wilson_interval

# ---------------------------------------------------------------------------
# Golden file
# ---------------------------------------------------------------------------

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures" / "report"
_GOLDEN = _FIXTURES_DIR / "golden-scorecard.md"

# ---------------------------------------------------------------------------
# Fixture ledger records
#
# Three scenarios × three tasks (two dev, one holdout):
#   bare              config_hash="aaa-bare"
#   series   config_hash="ccc-series"   (multi-run trial on task-beta)
#   single-long-session config_hash="bbb-single" (one infra error on task-beta)
#
# Grading records: bare vs series for dev tasks only.
# ---------------------------------------------------------------------------

_FIXTURE_RECORDS: list[dict] = [
    # ── bare / task-alpha / dev ──
    {
        "kind": "trial",
        "bank": "test-bank",
        "task_id": "task-alpha",
        "repeat": 0,
        "status": "completed",
        "dataset_version": "v1",
        "config_hash": "aaa-bare",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "verifier_results": {"criterion_1": True},
        "scenario": "bare",
        "holdout": False,
        "infra_error": False,
    },
    {
        "kind": "run",
        "bank": "test-bank",
        "task_id": "task-alpha",
        "repeat": 0,
        "usage": {"input_tokens": 100, "output_tokens": 50},
        "cost_usd_est": 0.005,
        "turns": 3,
        "duration": 10.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": "aaa-bare",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "scenario": "bare",
    },
    # ── bare / task-beta / dev ── (completed, fail)
    {
        "kind": "trial",
        "bank": "test-bank",
        "task_id": "task-beta",
        "repeat": 0,
        "status": "completed",
        "dataset_version": "v1",
        "config_hash": "aaa-bare",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "verifier_results": {"criterion_1": False},
        "scenario": "bare",
        "holdout": False,
        "infra_error": False,
    },
    {
        "kind": "run",
        "bank": "test-bank",
        "task_id": "task-beta",
        "repeat": 0,
        "usage": {"input_tokens": 200, "output_tokens": 80},
        "cost_usd_est": 0.008,
        "turns": 4,
        "duration": 12.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": "aaa-bare",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "scenario": "bare",
    },
    # ── single-long-session / task-alpha / dev ──
    {
        "kind": "trial",
        "bank": "test-bank",
        "task_id": "task-alpha",
        "repeat": 0,
        "status": "completed",
        "dataset_version": "v1",
        "config_hash": "bbb-single",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "verifier_results": {"criterion_1": True},
        "scenario": "single-long-session",
        "holdout": False,
        "infra_error": False,
    },
    {
        "kind": "run",
        "bank": "test-bank",
        "task_id": "task-alpha",
        "repeat": 0,
        "usage": {"input_tokens": 500, "output_tokens": 200},
        "cost_usd_est": 0.020,
        "turns": 10,
        "duration": 30.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": "bbb-single",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "scenario": "single-long-session",
    },
    # ── single-long-session / task-beta / dev ── INFRA ERROR
    {
        "kind": "trial",
        "bank": "test-bank",
        "task_id": "task-beta",
        "repeat": 0,
        "status": "errored",
        "dataset_version": "v1",
        "config_hash": "bbb-single",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "verifier_results": None,
        "scenario": "single-long-session",
        "holdout": False,
        "infra_error": True,
    },
    # ── series / task-alpha / dev ──
    {
        "kind": "trial",
        "bank": "test-bank",
        "task_id": "task-alpha",
        "repeat": 0,
        "status": "completed",
        "dataset_version": "v1",
        "config_hash": "ccc-series",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "series",
        "verifier_results": {"criterion_1": True},
        "scenario": "series",
        "holdout": False,
        "infra_error": False,
    },
    {
        "kind": "run",
        "bank": "test-bank",
        "task_id": "task-alpha",
        "repeat": 0,
        "usage": {"input_tokens": 150, "output_tokens": 60},
        "cost_usd_est": 0.006,
        "turns": 4,
        "duration": 15.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": "ccc-series",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "series",
        "scenario": "series",
    },
    # ── series / task-beta / dev ── (multi-run: 2 sessions)
    {
        "kind": "trial",
        "bank": "test-bank",
        "task_id": "task-beta",
        "repeat": 0,
        "status": "completed",
        "dataset_version": "v1",
        "config_hash": "ccc-series",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "series",
        "verifier_results": {"criterion_1": True},
        "scenario": "series",
        "holdout": False,
        "infra_error": False,
    },
    {
        "kind": "run",
        "bank": "test-bank",
        "task_id": "task-beta",
        "repeat": 0,
        "usage": {"input_tokens": 200, "output_tokens": 80},
        "cost_usd_est": 0.008,
        "turns": 5,
        "duration": 20.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": "ccc-series",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "series",
        "scenario": "series",
    },
    {
        "kind": "run",
        "bank": "test-bank",
        "task_id": "task-beta",
        "repeat": 0,
        "usage": {"input_tokens": 180, "output_tokens": 70},
        "cost_usd_est": 0.007,
        "turns": 4,
        "duration": 18.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": "ccc-series",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "series",
        "scenario": "series",
    },
    # ── bare / task-gamma / holdout ──
    {
        "kind": "trial",
        "bank": "test-bank",
        "task_id": "task-gamma",
        "repeat": 0,
        "status": "completed",
        "dataset_version": "v1",
        "config_hash": "aaa-bare",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "verifier_results": {"criterion_1": True},
        "scenario": "bare",
        "holdout": True,
        "infra_error": False,
    },
    {
        "kind": "run",
        "bank": "test-bank",
        "task_id": "task-gamma",
        "repeat": 0,
        "usage": {"input_tokens": 120, "output_tokens": 60},
        "cost_usd_est": 0.006,
        "turns": 3,
        "duration": 8.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": "aaa-bare",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "scenario": "bare",
    },
    # ── single-long-session / task-gamma / holdout ──
    {
        "kind": "trial",
        "bank": "test-bank",
        "task_id": "task-gamma",
        "repeat": 0,
        "status": "completed",
        "dataset_version": "v1",
        "config_hash": "bbb-single",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "verifier_results": {"criterion_1": True},
        "scenario": "single-long-session",
        "holdout": True,
        "infra_error": False,
    },
    {
        "kind": "run",
        "bank": "test-bank",
        "task_id": "task-gamma",
        "repeat": 0,
        "usage": {"input_tokens": 400, "output_tokens": 150},
        "cost_usd_est": 0.016,
        "turns": 8,
        "duration": 25.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": "bbb-single",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "scenario": "single-long-session",
    },
    # ── series / task-gamma / holdout ──
    {
        "kind": "trial",
        "bank": "test-bank",
        "task_id": "task-gamma",
        "repeat": 0,
        "status": "completed",
        "dataset_version": "v1",
        "config_hash": "ccc-series",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "series",
        "verifier_results": {"criterion_1": True},
        "scenario": "series",
        "holdout": True,
        "infra_error": False,
    },
    {
        "kind": "run",
        "bank": "test-bank",
        "task_id": "task-gamma",
        "repeat": 0,
        "usage": {"input_tokens": 160, "output_tokens": 65},
        "cost_usd_est": 0.007,
        "turns": 4,
        "duration": 12.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": "ccc-series",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "pin_level": "series",
        "scenario": "series",
    },
    # ── grading records: bare vs series, dev tasks ──
    {
        "kind": "grading",
        "bank": "test-bank",
        "task_id": "task-alpha",
        "repeat": 0,
        "verdict": "b",
        "dataset_version": "v1",
        "config_hash_a": "aaa-bare",
        "config_hash_b": "ccc-series",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "judge_config_hash": "jdg001",
        "judge_model": "claude-sonnet-4-6",
        "pin_level": "strong",
    },
    {
        "kind": "grading",
        "bank": "test-bank",
        "task_id": "task-beta",
        "repeat": 0,
        "verdict": "tie",
        "dataset_version": "v1",
        "config_hash_a": "aaa-bare",
        "config_hash_b": "ccc-series",
        "tool_git_sha": "gitsha1",
        "cli_version": "1.0.0",
        "judge_config_hash": "jdg001",
        "judge_model": "claude-sonnet-4-6",
        "pin_level": "strong",
    },
]


def _write_fixture(ledger_dir: pathlib.Path, bank: str) -> None:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    path = ledger_dir / f"{bank}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for rec in _FIXTURE_RECORDS:
            f.write(json.dumps(rec, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Wilson interval unit tests
# ---------------------------------------------------------------------------


def test_wilson_n_zero():
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_wilson_all_pass():
    lo, hi = wilson_interval(5, 5)
    assert 0.0 < lo < 1.0
    assert hi == 1.0


def test_wilson_none_pass():
    lo, hi = wilson_interval(0, 5)
    assert lo == 0.0
    assert 0.0 < hi < 1.0


def test_wilson_midpoint_symmetric():
    lo, hi = wilson_interval(1, 2)
    assert abs((lo + hi) / 2 - 0.5) < 1e-9


def test_wilson_bounds_in_unit_interval():
    for s, n in [(0, 1), (1, 1), (3, 10), (10, 10)]:
        lo, hi = wilson_interval(s, n)
        assert 0.0 <= lo <= hi <= 1.0


# ---------------------------------------------------------------------------
# Golden-file test
# ---------------------------------------------------------------------------


def test_golden_scorecard():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_dir = pathlib.Path(tmpdir) / "ledger"
        report_dir = pathlib.Path(tmpdir) / "report"
        _write_fixture(ledger_dir, "test-bank")
        render("test-bank", ledger_dir=ledger_dir, report_dir=report_dir)
        actual = (report_dir / "scorecard-test-bank.md").read_text(encoding="utf-8")

        if not _GOLDEN.exists():
            _FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
            _GOLDEN.write_text(actual, encoding="utf-8")
            print(f"  BOOTSTRAP: wrote {_GOLDEN}")
            return

        expected = _GOLDEN.read_text(encoding="utf-8")
        assert actual == expected, (
            f"Scorecard mismatch\n\n--- expected ---\n{expected}\n--- actual ---\n{actual}"
        )


# ---------------------------------------------------------------------------
# Idempotency test
# ---------------------------------------------------------------------------


def test_render_idempotent():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_dir = pathlib.Path(tmpdir) / "ledger"
        report_dir = pathlib.Path(tmpdir) / "report"
        _write_fixture(ledger_dir, "test-bank")
        render("test-bank", ledger_dir=ledger_dir, report_dir=report_dir)
        first = (report_dir / "scorecard-test-bank.md").read_text(encoding="utf-8")
        render("test-bank", ledger_dir=ledger_dir, report_dir=report_dir)
        second = (report_dir / "scorecard-test-bank.md").read_text(encoding="utf-8")
        assert first == second, "Second render differs from first — not idempotent"


# ---------------------------------------------------------------------------
# Content assertions
# ---------------------------------------------------------------------------


def _render_content() -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_dir = pathlib.Path(tmpdir) / "ledger"
        report_dir = pathlib.Path(tmpdir) / "report"
        _write_fixture(ledger_dir, "test-bank")
        render("test-bank", ledger_dir=ledger_dir, report_dir=report_dir)
        return (report_dir / "scorecard-test-bank.md").read_text(encoding="utf-8")


def test_per_criterion_table_present_and_discriminates():
    content = _render_content()
    assert "### Per-Criterion Pass Rates" in content
    # criterion_1: bare passes on alpha, fails on beta → 1/2 = 50%
    crit_rows = [ln for ln in content.splitlines() if ln.startswith("| criterion_1 |")]
    assert crit_rows, "No criterion_1 row in per-criterion table"
    assert "50.0% (1/2)" in crit_rows[0], crit_rows[0]


def test_per_criterion_table_sparse_and_excluded():
    """Shape branches of the per-criterion table: a criterion present in only one
    scenario renders the em-dash for the other; a scenario whose only completed
    trial has no dict verifier_results is excluded from the table columns entirely."""

    def _trial(scenario, ch, tid, vr):
        return {
            "kind": "trial",
            "bank": "sparse",
            "task_id": tid,
            "repeat": 0,
            "status": "completed",
            "dataset_version": "v1",
            "config_hash": ch,
            "tool_git_sha": "s",
            "cli_version": "1",
            "pin_level": "strong",
            "verifier_results": vr,
            "scenario": scenario,
            "holdout": False,
            "infra_error": False,
        }

    records = [
        _trial("alpha", "a", "t1", {"criterion_a": True, "criterion_b": True}),
        _trial("alpha", "a", "t2", {"criterion_a": True}),
        _trial("beta", "b", "t1", {"criterion_a": True}),  # never carries criterion_b
        _trial("noverif", "n", "t1", None),  # no dict verifier_results → excluded
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / "sparse.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        render("sparse", ledger_dir=ldgr, report_dir=rpt)
        content = (rpt / "scorecard-sparse.md").read_text(encoding="utf-8")

    header = next(ln for ln in content.splitlines() if ln.startswith("| Criterion |"))
    assert "alpha" in header and "beta" in header, header
    assert "noverif" not in header, f"scenario with no dict criteria leaked into columns: {header}"
    cb_row = next(ln for ln in content.splitlines() if ln.startswith("| criterion_b |"))
    assert "100.0% (1/1)" in cb_row, cb_row  # alpha: criterion_b seen once, true
    assert "—" in cb_row, f"beta should render em-dash for absent criterion_b: {cb_row}"


def test_verdict_lines_carry_n_ci_qualifier():
    content = _render_content()
    verdict_lines = [ln for ln in content.splitlines() if ln.startswith("- **")]
    assert verdict_lines, "No verdict lines found"
    for line in verdict_lines:
        assert "directional, not final" in line, f"Missing qualifier: {line}"
        assert "n=" in line, f"Missing n=: {line}"
        assert "Wilson 95% CI" in line, f"Missing CI: {line}"


def test_series_verdict_enumerates_arm_deltas():
    content = _render_content()
    series_lines = [ln for ln in content.splitlines() if "series" in ln and ln.startswith("- **")]
    assert series_lines, "No series verdict lines"
    for line in series_lines:
        for delta in (
            "human decomposition",
            "per-PR gates",
            "review/fix subagents",
            "engine settings",
        ):
            assert delta in line, f"Missing arm delta '{delta}': {line}"


def test_economy_sessions_per_trial_multi_run():
    content = _render_content()
    # series has task-alpha (1 run) and task-beta (2 runs): avg = 1.50
    assert "1.50" in content, "Expected sessions/trial of 1.50 for series"


def test_infra_error_excluded_from_denominator():
    content = _render_content()
    # single-long-session has 1 infra error, 1 completed → N=1 in pass rate
    rows = [ln for ln in content.splitlines() if "single-long-session" in ln and "|" in ln]
    assert rows, "No single-long-session rows found"
    assert "infra error(s) excluded" in content
    # Numerical guard: the pass-rate row where infra=1 must show N=1, not N=2.
    # A regression that counts infra-errored trials in the denominator would show N=2.
    pct_rows = [r for r in rows if "%" in r]
    assert pct_rows, "No pass-rate rows found for single-long-session"
    infra_rows = [r for r in pct_rows if r.split("|")[-2].strip() == "1"]
    assert infra_rows, "No single-long-session pass-rate row with infra=1"
    for row in infra_rows:
        cols = [c.strip() for c in row.split("|")]
        # Format: | scenario | pass | N | rate | CI | infra |
        n_col = cols[3] if len(cols) > 3 else ""
        assert n_col == "1", (
            f"Expected N=1 (infra trial excluded from denominator), got N={n_col!r} in: {row}"
        )


def test_economy_usd_reads_ledger_cost_field():
    """§11/D2: the Economy 'Est. USD' column reads the ledger run record's
    top-level cost_usd_est, NOT the never-emitted usage['cost_usd'] key.

    'ledgercost' carries cost only at top level → renders its USD.
    'legacyusage' carries cost only inside usage (the old, wrong key) → renders
    0.0000, proving the report no longer keys on usage['cost_usd'].
    """

    def _trial(sc, ch):
        return {
            "kind": "trial",
            "bank": "usd-src",
            "task_id": "task-t1",
            "repeat": 0,
            "status": "completed",
            "dataset_version": "v1",
            "config_hash": ch,
            "tool_git_sha": "s",
            "cli_version": "1",
            "pin_level": "strong",
            "verifier_results": {"correctness": True},
            "scenario": sc,
            "holdout": False,
            "infra_error": False,
        }

    def _run(sc, ch, usage, **extra):
        rec = {
            "kind": "run",
            "bank": "usd-src",
            "task_id": "task-t1",
            "repeat": 0,
            "usage": usage,
            "turns": 3,
            "duration": 10.0,
            "exit_code": 0,
            "dataset_version": "v1",
            "config_hash": ch,
            "tool_git_sha": "s",
            "cli_version": "1",
            "pin_level": "strong",
            "scenario": sc,
        }
        rec.update(extra)
        return rec

    records = [
        _trial("ledgercost", "lc"),
        _run("ledgercost", "lc", {"input_tokens": 100, "output_tokens": 50}, cost_usd_est=0.05),
        _trial("legacyusage", "lu"),
        # Cost only in the old usage key, no top-level field → must be ignored.
        _run("legacyusage", "lu", {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.99}),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / "usd-src.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        render("usd-src", ledger_dir=ldgr, report_dir=rpt)
        content = (rpt / "scorecard-usd-src.md").read_text(encoding="utf-8")

    # Scope to the Economy table (the "Est. USD" column); other tables also have
    # rows that start "| ledgercost |".
    lines = content.splitlines()
    econ_start = next(i for i, ln in enumerate(lines) if ln.startswith("### Economy"))
    econ = lines[econ_start:]
    lc_row = next(ln for ln in econ if ln.startswith("| ledgercost |"))
    lu_row = next(ln for ln in econ if ln.startswith("| legacyusage |"))
    assert lc_row.rstrip().endswith("| 0.0500 |"), lc_row
    assert lu_row.rstrip().endswith("| 0.0000 |"), lu_row


def test_holdout_section_separated_from_dev():
    content = _render_content()
    assert "## Dev Tasks" in content
    assert "## Holdout Tasks" in content
    dev_pos = content.index("## Dev Tasks")
    holdout_pos = content.index("## Holdout Tasks")
    assert dev_pos < holdout_pos


def test_pairwise_only_for_non_bare_scenarios():
    content = _render_content()
    assert "Pairwise vs Bare Anchor" in content
    lines = content.splitlines()
    pw_start = next((i for i, ln in enumerate(lines) if "Pairwise vs Bare Anchor" in ln), None)
    assert pw_start is not None
    # Collect table data rows from the pairwise section (skip blanks and header rows; stop at next heading)
    pw_rows = []
    in_table = False
    for line in lines[pw_start + 1 :]:
        if line.startswith("#"):
            break
        if line.startswith("|"):
            in_table = True
            if "Scenario" not in line and not line.startswith("|---"):
                pw_rows.append(line)
        elif in_table and line.strip() == "":
            break
    assert pw_rows, "No pairwise data rows found"
    assert not any(r.strip().startswith("| bare ") for r in pw_rows), (
        "bare should not appear as a pairwise row — it is the anchor"
    )


def test_output_file_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_dir = pathlib.Path(tmpdir) / "ledger"
        report_dir = pathlib.Path(tmpdir) / "report"
        _write_fixture(ledger_dir, "test-bank")
        out = render("test-bank", ledger_dir=ledger_dir, report_dir=report_dir)
        assert out == report_dir / "scorecard-test-bank.md"
        assert out.exists()


def test_render_rejects_path_traversal():
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        try:
            render("../../etc/passwd", ledger_dir=ldgr, report_dir=rpt)
            raise AssertionError("Expected ValueError for path-traversal bank name")
        except ValueError:
            pass


def test_verdict_infra_only_no_scored_fraction():
    # A scenario where every trial hit an infra error (n=0, infra=1) must not
    # render a misleading "0/0" fraction in its verdict line.
    records = [
        {
            "kind": "trial",
            "bank": "infra-only",
            "task_id": "task-x",
            "repeat": 0,
            "status": "errored",
            "dataset_version": "v1",
            "config_hash": "iii-sc",
            "tool_git_sha": "sha1",
            "cli_version": "1.0.0",
            "pin_level": "strong",
            "verifier_results": None,
            "scenario": "infra-sc",
            "holdout": False,
            "infra_error": True,
        }
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / "infra-only.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        render("infra-only", ledger_dir=ldgr, report_dir=rpt)
        content = (rpt / "scorecard-infra-only.md").read_text(encoding="utf-8")
    verdict_lines = [ln for ln in content.splitlines() if ln.startswith("- **")]
    assert verdict_lines, "No verdict lines for infra-only scenario"
    for line in verdict_lines:
        assert "0/0" not in line, f"Misleading '0/0' fraction in infra-only verdict: {line}"
        assert "1 infra error(s) excluded" in line, f"Missing infra note: {line}"
        assert "directional, not final" in line, f"Missing qualifier: {line}"


def test_economy_omitted_when_no_completed_trials():
    # When all trials in a section are infra-errored, the Economy header must not
    # be emitted without any data rows (no orphaned Markdown table header).
    records = [
        {
            "kind": "trial",
            "bank": "all-infra",
            "task_id": "task-x",
            "repeat": 0,
            "status": "errored",
            "dataset_version": "v1",
            "config_hash": "iii-sc",
            "tool_git_sha": "sha1",
            "cli_version": "1.0.0",
            "pin_level": "strong",
            "verifier_results": None,
            "scenario": "infra-sc",
            "holdout": False,
            "infra_error": True,
        }
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / "all-infra.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        render("all-infra", ledger_dir=ldgr, report_dir=rpt)
        content = (rpt / "scorecard-all-infra.md").read_text(encoding="utf-8")
    # Economy section must be absent — no data rows to show
    assert "### Economy" not in content, (
        "Economy header emitted with no data rows (all trials are infra-errored)"
    )


# ---------------------------------------------------------------------------
# Efficiency view tests (§9)
# ---------------------------------------------------------------------------


def test_efficiency_section_present():
    content = _render_content()
    assert "### Efficiency" in content
    assert "Quality / 100k Tok" in content
    assert "Pareto" in content


def _make_efficiency_records(bank: str, arms: list[dict]) -> list[dict]:
    """Build minimal trial+run records for efficiency testing.

    Each arm entry: {"name": str, "ch": str, "passes": bool, "in": int, "out": int}
    All on a single task ("task-t1", dev, repeat=0).
    """
    records = []
    for arm in arms:
        records.append(
            {
                "kind": "trial",
                "bank": bank,
                "task_id": "task-t1",
                "repeat": 0,
                "status": "completed",
                "dataset_version": "v1",
                "config_hash": arm["ch"],
                "tool_git_sha": "sha1",
                "cli_version": "1.0.0",
                "pin_level": "strong",
                "verifier_results": {"correctness": arm["passes"]},
                "scenario": arm["name"],
                "holdout": False,
                "infra_error": False,
            }
        )
        records.append(
            {
                "kind": "run",
                "bank": bank,
                "task_id": "task-t1",
                "repeat": 0,
                "usage": {"input_tokens": arm["in"], "output_tokens": arm["out"]},
                "turns": 5,
                "duration": 30.0,
                "exit_code": 0,
                "dataset_version": "v1",
                "config_hash": arm["ch"],
                "tool_git_sha": "sha1",
                "cli_version": "1.0.0",
                "pin_level": "strong",
                "scenario": arm["name"],
            }
        )
    return records


def _render_efficiency_fixture(bank: str, arms: list[dict]) -> str:
    records = _make_efficiency_records(bank, arms)
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / f"{bank}.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        render(bank, ledger_dir=ldgr, report_dir=rpt)
        return (rpt / f"scorecard-{bank}.md").read_text(encoding="utf-8")


def test_efficiency_pareto_dominance_flagged():
    # "efficient" (quality=1.0, tokens=150) dominates "costly" (quality=1.0, tokens=750).
    # "costly" does NOT dominate "efficient" (same quality but more tokens).
    content = _render_efficiency_fixture(
        "pareto-dom",
        [
            {"name": "efficient", "ch": "eff-h", "passes": True, "in": 100, "out": 50},
            {"name": "costly", "ch": "cos-h", "passes": True, "in": 500, "out": 250},
        ],
    )
    lines = content.splitlines()
    eff_rows = [ln for ln in lines if "|" in ln and "★" in ln]
    assert eff_rows, "Expected at least one ★-flagged row in efficiency table"
    # "efficient" must carry ★; "costly" must not
    assert any("efficient" in r for r in eff_rows), "efficient arm should have ★"
    assert not any("costly" in r for r in eff_rows), "costly arm should not have ★"


def test_efficiency_tradeoff_both_on_frontier():
    # "hi-quality" (quality=1.0, tokens=500) vs "lo-cost" (quality=0.0, tokens=100):
    # neither dominates the other — quality wins one axis, tokens the other — so
    # BOTH are on the Pareto frontier and both are starred. (The prior star meaning,
    # "beats someone", starred neither; the correct "non-dominated" meaning stars both.)
    content = _render_efficiency_fixture(
        "pareto-trade",
        [
            {"name": "hi-quality", "ch": "hq-h", "passes": True, "in": 400, "out": 100},
            {"name": "lo-cost", "ch": "lc-h", "passes": False, "in": 80, "out": 20},
        ],
    )
    starred = [ln for ln in content.splitlines() if "|" in ln and "★" in ln]
    assert any("hi-quality" in r for r in starred), "hi-quality is non-dominated → frontier"
    assert any("lo-cost" in r for r in starred), (
        "lo-cost is the cheapest → non-dominated → frontier"
    )


def test_efficiency_quality_per_100k_computed():
    # bare in dev tasks: quality=0.5, mean_total=(150+280)/2=215 tokens
    # → qp100k = 0.5 * 100000 / 215 ≈ 232.56
    content = _render_content()
    assert "232.56" in content, "Expected quality-per-100k ≈ 232.56 for bare in dev tasks"


def test_efficiency_series_pareto_dominates_single_in_dev():
    # From the main fixture, in dev tasks:
    # series: quality=1.0, mean_total=370 tokens  → non-dominated → ★
    # single-long-session: quality=1.0, mean_total=700 tokens → dominated by series
    #   (same quality, more tokens) → no ★
    # bare: quality=0.5, mean_total=215 tokens → the CHEAPEST arm; no arm has both
    #   >= quality and <= tokens, so bare is on the frontier too → ★
    content = _render_content()
    # Dev section: find the Efficiency table and validate flags
    lines = content.splitlines()
    # Locate dev section efficiency table rows (before holdout section)
    holdout_pos = next((i for i, ln in enumerate(lines) if ln.startswith("## Holdout")), len(lines))
    dev_lines = lines[:holdout_pos]
    series_eff = [ln for ln in dev_lines if "series" in ln and "★" in ln]
    single_eff = [ln for ln in dev_lines if "single-long-session" in ln and "★" in ln]
    bare_eff = [ln for ln in dev_lines if ln.strip().startswith("| bare |") and "★" in ln]
    assert series_eff, "series should have ★ in dev efficiency table"
    assert not single_eff, "single-long-session is dominated by series → no ★"
    assert bare_eff, "bare is the cheapest arm (non-dominated) → ★ on the frontier"


def test_efficiency_omitted_when_all_infra():
    # Mirror of test_economy_omitted_when_no_completed_trials: Efficiency header
    # must also be absent when there are no completed trials.
    records = [
        {
            "kind": "trial",
            "bank": "all-infra2",
            "task_id": "task-x",
            "repeat": 0,
            "status": "errored",
            "dataset_version": "v1",
            "config_hash": "iii-sc",
            "tool_git_sha": "sha1",
            "cli_version": "1.0.0",
            "pin_level": "strong",
            "verifier_results": None,
            "scenario": "infra-sc",
            "holdout": False,
            "infra_error": True,
        }
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / "all-infra2.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        render("all-infra2", ledger_dir=ldgr, report_dir=rpt)
        content = (rpt / "scorecard-all-infra2.md").read_text(encoding="utf-8")
    assert "### Efficiency" not in content, "Efficiency header emitted with no completed trials"


# ---------------------------------------------------------------------------
# Economy reconciliation — run/trial join must not orphan or double-count
# (real ledger structure: cli.py appends a trial's runs BEFORE its trial line,
# and a ledger RunRecord carries NO `scenario` field)
# ---------------------------------------------------------------------------


def _real_run(bank, tid, rep, ch, tin, tout, cost=0.0):
    """A ledger run record shaped exactly as cli.py writes it: NO scenario field."""
    return {
        "kind": "run",
        "bank": bank,
        "task_id": tid,
        "repeat": rep,
        "usage": {"input_tokens": tin, "output_tokens": tout},
        "turns": 4,
        "duration": 12.0,
        "exit_code": 0,
        "dataset_version": "v1",
        "config_hash": ch,
        "tool_git_sha": "sha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "cost_usd_est": cost,
    }


def _real_trial(bank, tid, rep, ch, name, status="completed", passes=True):
    return {
        "kind": "trial",
        "bank": bank,
        "task_id": tid,
        "repeat": rep,
        "status": status,
        "dataset_version": "v1",
        "config_hash": ch,
        "tool_git_sha": "sha1",
        "cli_version": "1.0.0",
        "pin_level": "strong",
        "verifier_results": {"correctness": passes} if status == "completed" else None,
        "scenario": name,
        "holdout": False,
        "infra_error": False,
    }


def _economy_tokens(content: str, sc: str) -> int:
    """Pull the Tokens cell for scenario *sc* from the Economy table.

    Scoped to the `### Economy` section so it never matches the Pass-Rates or
    Efficiency table (which also have a scenario name in column 1).
    """
    lines = content.splitlines()
    try:
        start = lines.index("### Economy")
    except ValueError as exc:
        raise AssertionError(f"no Economy section in:\n{content}") from exc
    for ln in lines[start:]:
        if ln.startswith("###") and ln != "### Economy":
            break  # next section — stop before Efficiency
        cols = [c.strip() for c in ln.split("|")]
        # | scenario | tokens | turns | wall | sessions/trial | usd |
        if len(cols) >= 7 and cols[1] == sc and cols[2].isdigit():
            return int(cols[2])
    raise AssertionError(f"no Economy row for {sc!r} in:\n{content}")


def test_economy_no_orphan_of_first_trial_runs():
    """Every arm's FIRST trial's economy must be attributed, not orphaned.

    Regression for the run/scenario join bug: runs are written before their
    trial and carry no scenario field, so a single incremental-map pass keyed
    the first trial's runs under the raw config_hash and dropped them from
    Economy (12.6% of tokens on a real matrix). Two arms, faithful ordering.
    """
    bank = "recon"
    records = [
        # bare / t1 (FIRST trial of h-bare — the orphan victim): 100+50 = 150 tok
        _real_run(bank, "t1", 0, "h-bare", 100, 50),
        _real_trial(bank, "t1", 0, "h-bare", "bare"),
        # bare / t2: 10+5 = 15 tok
        _real_run(bank, "t2", 0, "h-bare", 10, 5),
        _real_trial(bank, "t2", 0, "h-bare", "bare"),
        # treat / t1 (FIRST and only trial of h-treat — fully orphaned when buggy)
        _real_run(bank, "t1", 0, "h-treat", 200, 80),
        _real_trial(bank, "t1", 0, "h-treat", "treat"),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / f"{bank}.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        render(bank, ledger_dir=ldgr, report_dir=rpt)
        content = (rpt / f"scorecard-{bank}.md").read_text(encoding="utf-8")
    assert _economy_tokens(content, "bare") == 165, (
        "bare economy dropped its first trial's runs (orphan join bug)"
    )
    assert _economy_tokens(content, "treat") == 280, (
        "treat economy fully orphaned (single trial is always the arm's first)"
    )


def test_duplicate_completed_cell_warns():
    """Two completed trial lines for one resume-key cell must warn loudly.

    A resume never re-runs a completed cell, so a duplicate completed line means
    the same scored cell was recorded twice and its runs would be summed twice in
    Economy. The renderer cannot un-sum runs it cannot attribute to an attempt, so
    it warns (silent-wrong -> loud-visible) rather than double-count silently.
    """
    bank = "dup-complete"
    records = [
        _real_run(bank, "t1", 0, "h-bare", 100, 50),
        _real_trial(bank, "t1", 0, "h-bare", "bare"),
        # duplicate completed line for the SAME (dataset_version, config_hash, task, repeat)
        _real_run(bank, "t1", 0, "h-bare", 100, 50),
        _real_trial(bank, "t1", 0, "h-bare", "bare"),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / f"{bank}.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            render(bank, ledger_dir=ldgr, report_dir=rpt)
        msgs = [str(w.message) for w in caught]
    assert any("duplicate completed trial" in m for m in msgs), (
        f"expected a duplicate-completed-cell warning, got: {msgs}"
    )


def test_dangling_run_without_trial_line_warns():
    """A run whose config_hash appears in no trial line must warn, not vanish silently.

    Its economy can't be attributed to any arm (the raw hash is never in all_sc), so
    the renderer surfaces it instead of dropping it without a trace.
    """
    bank = "dangling"
    records = [
        _real_run(bank, "t1", 0, "h-ghost", 500, 100),  # no trial record for h-ghost
        _real_run(bank, "t1", 0, "h-known", 10, 5),
        _real_trial(bank, "t1", 0, "h-known", "known"),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / f"{bank}.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            render(bank, ledger_dir=ldgr, report_dir=rpt)
        msgs = [str(w.message) for w in caught]
    assert any("has no trial line" in m for m in msgs), (
        f"expected a dangling-run warning, got: {msgs}"
    )


def test_errored_rerun_does_not_inflate_completed_cell_denominator():
    """An errored attempt sharing a cell with siblings must not be double-scored.

    Real ledgers accumulate errored re-runs (e.g. exprlang errored 7x). Those
    errored trials must not appear as completed and must not add to the pass-rate
    denominator; only the single completed attempt counts.
    """
    bank = "errored-rerun"
    records = [
        _real_run(bank, "t1", 0, "h-bare", 999, 0),
        _real_trial(bank, "t1", 0, "h-bare", "bare", status="errored", passes=False),
        _real_run(bank, "t1", 0, "h-bare", 20, 10),
        _real_trial(bank, "t1", 0, "h-bare", "bare", status="completed", passes=True),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / f"{bank}.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        render(bank, ledger_dir=ldgr, report_dir=rpt)
        content = (rpt / f"scorecard-{bank}.md").read_text(encoding="utf-8")
    # Pass-rate row: | bare | 1 | 1 | 100.0% | ... | 0 |  (N=1, not N=2)
    rows = [ln for ln in content.splitlines() if "| bare |" in ln and "%" in ln]
    assert rows, f"no bare pass-rate row in:\n{content}"
    cols = [c.strip() for c in rows[0].split("|")]
    assert cols[3] == "1", f"errored re-run inflated N (expected N=1): {rows[0]}"


def test_efficiency_pareto_dominated_middle_not_flagged():
    """The Pareto star means 'on the efficiency frontier' (non-dominated).

    Three arms: top(q1,150 tok) dominates mid(q1,300) which dominates bot(q0,450).
    Only top is on the frontier. The prior 'flags any arm that beats someone' bug
    starred mid (it beats bot) though top strictly dominates it.
    """
    content = _render_efficiency_fixture(
        "pareto-mid",
        [
            {"name": "top", "ch": "top-h", "passes": True, "in": 100, "out": 50},
            {"name": "mid", "ch": "mid-h", "passes": True, "in": 200, "out": 100},
            {"name": "bot", "ch": "bot-h", "passes": False, "in": 300, "out": 150},
        ],
    )
    starred = [ln for ln in content.splitlines() if "|" in ln and "★" in ln]
    assert any("| top |" in r for r in starred), "top (frontier) must be starred"
    assert not any("| mid |" in r for r in starred), (
        "mid is strictly dominated by top and must NOT be starred"
    )
    assert not any("| bot |" in r for r in starred), "bot is dominated and must NOT be starred"


# ---------------------------------------------------------------------------
# Stdlib runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _tests = [
        test_wilson_n_zero,
        test_wilson_all_pass,
        test_wilson_none_pass,
        test_wilson_midpoint_symmetric,
        test_wilson_bounds_in_unit_interval,
        test_golden_scorecard,
        test_render_idempotent,
        test_per_criterion_table_present_and_discriminates,
        test_per_criterion_table_sparse_and_excluded,
        test_verdict_lines_carry_n_ci_qualifier,
        test_series_verdict_enumerates_arm_deltas,
        test_economy_sessions_per_trial_multi_run,
        test_economy_usd_reads_ledger_cost_field,
        test_infra_error_excluded_from_denominator,
        test_holdout_section_separated_from_dev,
        test_pairwise_only_for_non_bare_scenarios,
        test_output_file_path,
        test_render_rejects_path_traversal,
        test_verdict_infra_only_no_scored_fraction,
        test_economy_omitted_when_no_completed_trials,
        test_efficiency_section_present,
        test_efficiency_pareto_dominance_flagged,
        test_efficiency_tradeoff_both_on_frontier,
        test_efficiency_quality_per_100k_computed,
        test_efficiency_series_pareto_dominates_single_in_dev,
        test_efficiency_omitted_when_all_infra,
        test_economy_no_orphan_of_first_trial_runs,
        test_duplicate_completed_cell_warns,
        test_dangling_run_without_trial_line_warns,
        test_errored_rerun_does_not_inflate_completed_cell_denominator,
        test_efficiency_pareto_dominated_middle_not_flagged,
    ]
    _failed: list[str] = []
    for _t in _tests:
        try:
            _t()
            print(f"  PASS  {_t.__name__}")
        except Exception as _e:
            import traceback

            print(f"  FAIL  {_t.__name__}: {_e}")
            traceback.print_exc()
            _failed.append(_t.__name__)
    print(f"\n{len(_tests) - len(_failed)}/{len(_tests)} passed")
    if _failed:
        sys.exit(1)
