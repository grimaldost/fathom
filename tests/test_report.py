"""Tests for fathom.report — stdlib-runnable.

Run via pytest or directly:  python tests/test_report.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import warnings

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from fathom.report import per_trial_rows, render, render_per_trial, wilson_interval

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
#   series            config_hash="ccc-series"   (multi-run trial on task-beta)
#   single-session    config_hash="bbb-single"   (one infra error on task-beta)
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
    # ── single-session / task-alpha / dev ──
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
        "scenario": "single-session",
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
        "scenario": "single-session",
    },
    # ── single-session / task-beta / dev ── INFRA ERROR
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
        "scenario": "single-session",
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
    # ── single-session / task-gamma / holdout ──
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
        "scenario": "single-session",
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
        "scenario": "single-session",
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


def test_verdict_carries_cluster_count_and_ci_caveat():
    """Estimator honesty: the pooled Wilson CI
    pools correlated repeats + heterogeneous tasks as independent, so the scorecard
    must (1) surface the cluster count K (distinct tasks) beside n so the design
    effect is visible, and (2) carry an explicit clustering caveat mirroring
    ADR-0007 D3 — a heuristic width, not exact 95% coverage."""
    content = _render_content()
    # bare's dev tasks are task-alpha + task-beta → K=2 distinct tasks.
    bare_verdict = next(
        ln for ln in content.splitlines() if ln.startswith("- **bare**") and "n=" in ln
    )
    assert "K=2" in bare_verdict, f"verdict should surface cluster count K=2: {bare_verdict}"
    # The clustering caveat must be present (not just the generic 'directional' tag).
    low = content.lower()
    assert "heuristic width" in low, "missing the heuristic-width CI caveat"
    assert "correlated repeats" in low, "caveat must name correlated repeats"
    assert "adr-0007" in low, "caveat should cite the calibration precedent (ADR-0007 D3)"


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
    # single-session has 1 infra error, 1 completed → N=1 in pass rate
    rows = [ln for ln in content.splitlines() if "single-session" in ln and "|" in ln]
    assert rows, "No single-session rows found"
    assert "infra error(s) excluded" in content
    # Numerical guard: the pass-rate row where infra=1 must show N=1, not N=2.
    # A regression that counts infra-errored trials in the denominator would show N=2.
    pct_rows = [r for r in rows if "%" in r]
    assert pct_rows, "No pass-rate rows found for single-session"
    infra_rows = [r for r in pct_rows if r.split("|")[-2].strip() == "1"]
    assert infra_rows, "No single-session pass-rate row with infra=1"
    for row in infra_rows:
        cols = [c.strip() for c in row.split("|")]
        # Format: | scenario | pass | N | rate | CI | infra |
        n_col = cols[3] if len(cols) > 3 else ""
        assert n_col == "1", (
            f"Expected N=1 (infra trial excluded from denominator), got N={n_col!r} in: {row}"
        )


def test_economy_usd_reads_ledger_cost_field():
    """The Economy 'Est. USD' column reads the ledger run record's
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
    # Collect table data rows from the pairwise section (skip blanks and header rows;
    # stop at next heading)
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


def _dv_trial(dv, sc, ch, tid, rep, passed):
    return {
        "kind": "trial",
        "bank": "dv-bank",
        "task_id": tid,
        "repeat": rep,
        "status": "completed",
        "dataset_version": dv,
        "config_hash": ch,
        "tool_git_sha": "s",
        "cli_version": "1",
        "pin_level": "strong",
        "verifier_results": {"c": passed},
        "scenario": sc,
        "holdout": False,
        "infra_error": False,
    }


def _dv_run(dv, sc, ch, tid, rep):
    return {
        "kind": "run",
        "bank": "dv-bank",
        "task_id": tid,
        "repeat": rep,
        "usage": {"input_tokens": 100, "output_tokens": 50},
        "cost_usd_est": 0.01,
        "turns": 3,
        "duration": 10.0,
        "exit_code": 0,
        "dataset_version": dv,
        "config_hash": ch,
        "tool_git_sha": "s",
        "cli_version": "1",
        "pin_level": "strong",
        "scenario": sc,
    }


def test_multiple_dataset_versions_scoped_to_current():
    """A bumped dataset_version must NOT silently conflate old + new task versions
    under one arm. The scorecard reflects the CURRENT
    (last-appended) dataset_version only; older-dv trials are excluded (not mixed)
    and their exclusion is surfaced, never silent.

    Ledger: bare/task-x under dv 'v1' (easy task, reps 0-3 all PASS) then dv 'v2'
    (hardened task, reps 0-1 all FAIL — only two re-run so far). The buggy renderer
    keyed trials by (scenario, task, repeat) with no dataset_version, so last-write-
    wins kept v2 for reps 0-1 but v1's reps 2-3 leaked in — rendering a conflated
    2/4 = 50%. Scoping to the current dv (v2) must render 0/2 = 0%.
    """
    records = []
    for rep in range(4):  # v1: easy task, all pass (older)
        records += [
            _dv_trial("v1", "bare", "aaa", "task-x", rep, True),
            _dv_run("v1", "bare", "aaa", "task-x", rep),
        ]
    for rep in range(2):  # v2: hardened task, all fail (current, only 2 re-run)
        records += [
            _dv_trial("v2", "bare", "aaa", "task-x", rep, False),
            _dv_run("v2", "bare", "aaa", "task-x", rep),
        ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ldgr = pathlib.Path(tmpdir) / "ledger"
        rpt = pathlib.Path(tmpdir) / "report"
        ldgr.mkdir(parents=True, exist_ok=True)
        with open(ldgr / "dv-bank.jsonl", "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            render("dv-bank", ledger_dir=ldgr, report_dir=rpt)
        content = (rpt / "scorecard-dv-bank.md").read_text(encoding="utf-8")

    # Current dv is v2 (both FAIL) → bare must be 0/2 (0%), NOT the conflated 2/4 (50%).
    rate_rows = [ln for ln in content.splitlines() if ln.startswith("| bare |") and "%" in ln]
    assert rate_rows, f"no bare pass-rate row found in:\n{content}"
    cols = [c.strip() for c in rate_rows[0].split("|")]
    # | scenario | pass | N | rate | CI | infra |
    assert cols[2] == "0", f"expected pass=0 (v2 only), got {cols[2]!r} in {rate_rows[0]}"
    assert cols[3] == "2", f"expected N=2 (v2 only, not conflated with v1), got {cols[3]!r}"
    assert cols[4] == "0.0%", f"expected 0.0% (v2 fails), got {cols[4]!r}"

    # The exclusion must be surfaced, not silent (data-contract discipline).
    assert any("dataset_version" in str(w.message) for w in caught), (
        "expected a warning that older dataset_version trials were excluded"
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
    # single-session: quality=1.0, mean_total=700 tokens → dominated by series
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
    single_eff = [ln for ln in dev_lines if "single-session" in ln and "★" in ln]
    bare_eff = [ln for ln in dev_lines if ln.strip().startswith("| bare |") and "★" in ln]
    assert series_eff, "series should have ★ in dev efficiency table"
    assert not single_eff, "single-session is dominated by series → no ★"
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
        # | scenario | N | tokens | tokens spread | turns | turns spread |
        # | wall | sessions/trial | usd |   (N and the two spreads included)
        if len(cols) >= 10 and cols[1] == sc and cols[3].isdigit():
            return int(cols[3])
    raise AssertionError(f"no Economy row for {sc!r} in:\n{content}")


def test_economy_no_orphan_of_first_trial_runs():
    """Every arm's FIRST trial's economy must be attributed, not orphaned.

    Regression for the run/scenario join bug: runs are written before their
    trial and carry no scenario field, so a single incremental-map pass keyed
    the first trial's runs under the raw config_hash and dropped them from
    Economy. Two arms, faithful ordering.
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

    A ledger can accumulate errored re-runs of one cell. Those errored trials must
    not appear as completed and must not add to the pass-rate denominator; only the
    single completed attempt counts.
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


def test_calibration_metadata_is_read_from_the_tasks_dir_given():
    """The scorecard reads a bank's scores.toml from its tasks_dir, not the working dir."""
    import contextlib

    from fathom.report import _load_task_meta

    with tempfile.TemporaryDirectory() as tmp:
        tasks = pathlib.Path(tmp) / "data" / "tasks"
        bank = tasks / "cal"
        (bank / "t1").mkdir(parents=True)
        (bank / "bank.toml").write_text(
            'name = "cal"\ndataset_version = "1"\nholdout = []\n', encoding="utf-8"
        )
        (bank / "t1" / "task.toml").write_text(
            'id = "t1"\ninstruction = "x"\n[limits]\ntrial_timeout_s = 1\n'
            '[verify]\nentry = "verify.py"\nhard_criteria = ["correctness"]\n',
            encoding="utf-8",
        )
        (bank / "scores.toml").write_text("[scores]\nt1 = 0.5\n", encoding="utf-8")
        elsewhere = pathlib.Path(tmp) / "elsewhere"
        elsewhere.mkdir()
        with contextlib.chdir(elsewhere):
            meta = _load_task_meta("cal", tasks)
        assert meta == {"t1": {"score": 0.5, "hard_criteria": ["correctness"]}}


# ---------------------------------------------------------------------------
# Saturation banner: every arm at the pass ceiling points at the economy axis
# ---------------------------------------------------------------------------


def _sat_records(passing: dict[str, int], n_tasks: int, *, reps: int = 1) -> list[dict]:
    """One trial per (arm, task, repeat); arm `a` passes the first passing[a] tasks."""
    records = []
    for sc, k in passing.items():
        for i in range(n_tasks):
            for rep in range(reps):
                records.append(_hc_trial(sc, f"t{i:02d}", rep, {"ok": i < k}))
    return records


def _banner(content: str) -> list[str]:
    return [line for line in content.splitlines() if line.startswith("> **Saturated:**")]


def test_the_banner_prints_k_and_n_when_every_arm_is_at_the_ceiling(tmp_path):
    content = _hc_render(tmp_path, _sat_records({"bare": 3, "nudge": 3}, 3))
    assert _banner(content) == [
        (
            "> **Saturated:** every arm passes at least 3 of 3 tasks, so the pass rate cannot "
            "separate the arms here; compare them on Economy and Efficiency, or make the bank "
            "harder."
        )
    ]


def test_the_banner_follows_the_pass_rates_table(tmp_path):
    content = _hc_render(tmp_path, _sat_records({"bare": 2, "nudge": 2}, 2))
    assert (
        content.index("### Pass Rates")
        < content.index("> **Saturated:**")
        < content.index("### Verdicts")
    )


def test_a_single_arm_ledger_prints_no_banner(tmp_path):
    assert _banner(_hc_render(tmp_path, _sat_records({"bare": 3}, 3))) == []


def test_one_task_both_arms_passing_prints_the_banner(tmp_path):
    content = _hc_render(tmp_path, _sat_records({"bare": 1, "nudge": 1}, 1))
    (line,) = _banner(content)
    assert "at least 1 of 1 tasks" in line


def test_eight_of_ten_for_one_arm_prints_no_banner(tmp_path):
    # K = ceil(0.9 x 10) = 9, and bare passes only 8 tasks.
    assert _banner(_hc_render(tmp_path, _sat_records({"bare": 8, "nudge": 10}, 10))) == []


def test_nine_of_ten_for_every_arm_prints_the_banner(tmp_path):
    content = _hc_render(tmp_path, _sat_records({"bare": 9, "nudge": 10}, 10))
    (line,) = _banner(content)
    assert "at least 9 of 10 tasks" in line


def test_a_task_is_passed_when_half_its_completed_trials_pass(tmp_path):
    # bare passes 1 of 2 repeats on the only task (half: a pass); nudge passes 0 of 2.
    records = [
        _hc_trial("bare", "t1", 0, {"ok": True}),
        _hc_trial("bare", "t1", 1, {"ok": False}),
        _hc_trial("nudge", "t1", 0, {"ok": False}),
        _hc_trial("nudge", "t1", 1, {"ok": False}),
    ]
    assert _banner(_hc_render(tmp_path / "a", records)) == []
    records[2] = _hc_trial("nudge", "t1", 0, {"ok": True})
    assert len(_banner(_hc_render(tmp_path / "b", records))) == 1


def test_a_task_passed_by_less_than_half_its_trials_does_not_count(tmp_path):
    records = [
        _hc_trial("bare", "t1", 0, {"ok": True}),
        _hc_trial("bare", "t1", 1, {"ok": False}),
        _hc_trial("bare", "t1", 2, {"ok": False}),
        _hc_trial("nudge", "t1", 0, {"ok": True}),
        _hc_trial("nudge", "t1", 1, {"ok": True}),
        _hc_trial("nudge", "t1", 2, {"ok": True}),
    ]
    assert _banner(_hc_render(tmp_path, records)) == []


def test_errored_and_infra_trials_do_not_decide_a_task(tmp_path):
    records = [
        _hc_trial("bare", "t1", 0, {"ok": True}),
        _hc_trial("bare", "t1", 1, {"ok": False}, status="errored"),
        _hc_trial("bare", "t1", 2, {"ok": False}, infra=True),
        _hc_trial("nudge", "t1", 0, {"ok": True}),
    ]
    assert len(_banner(_hc_render(tmp_path, records))) == 1


def test_an_arm_with_no_completed_trial_is_not_counted_as_an_arm(tmp_path):
    # nudge has only an infra error, so one arm remains and there is nothing to separate.
    records = [
        _hc_trial("bare", "t1", 0, {"ok": True}),
        _hc_trial("nudge", "t1", 0, {"ok": False}, infra=True),
    ]
    assert _banner(_hc_render(tmp_path, records)) == []


def test_the_golden_banner_is_in_the_saturated_holdout_section_only():
    # Dev Tasks: bare passes 1 of 2 tasks, below K = 2. Holdout: every arm passes its 1 task.
    dev, holdout = _GOLDEN.read_text(encoding="utf-8").split("## Holdout Tasks")
    assert "Saturated" not in dev
    assert "> **Saturated:** every arm passes at least 1 of 1 tasks" in holdout


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


# --- Calibration section text: pinned so a scorecard renders the same across releases ---


def test_calibration_heading_is_pinned():
    from fathom.report import calibration_heading

    assert calibration_heading(is_context=True) == "## Context-Size Calibration"
    assert calibration_heading(is_context=False) == "## Model-Tier Calibration"


def test_substrate_note_names_the_file_relative_to_the_data_root(tmp_path):
    from fathom.report import substrate_display_path

    inside = tmp_path / "report" / "routing-substrate-b.json"
    assert substrate_display_path(inside, root=tmp_path) == "report/routing-substrate-b.json"
    outside = tmp_path.parent / "elsewhere" / "routing-substrate-b.json"
    assert substrate_display_path(outside, root=tmp_path) == outside.as_posix()


# ---------------------------------------------------------------------------
# A chosen historical dataset_version
# ---------------------------------------------------------------------------


def _two_version_records() -> list[dict]:
    """bare/task-x: v1 (reps 0-3, all pass), then v2 (reps 0-1, all fail)."""
    records = []
    for rep in range(4):
        records += [
            _dv_trial("v1", "bare", "aaa", "task-x", rep, True),
            _dv_run("v1", "bare", "aaa", "task-x", rep),
        ]
    for rep in range(2):
        records += [
            _dv_trial("v2", "bare", "aaa", "task-x", rep, False),
            _dv_run("v2", "bare", "aaa", "task-x", rep),
        ]
    return records


def _render_two_versions(tmp_path, **kwargs):
    ldgr = tmp_path / "ledger"
    rpt = tmp_path / "report"
    ldgr.mkdir(parents=True)
    with open(ldgr / "dv-bank.jsonl", "w", encoding="utf-8") as f:
        for rec in _two_version_records():
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = render("dv-bank", ledger_dir=ldgr, report_dir=rpt, **kwargs)
    return out, rpt, caught


def _bare_rate_cols(content: str) -> list[str]:
    rows = [ln for ln in content.splitlines() if ln.startswith("| bare |") and "%" in ln]
    assert rows, content
    return [c.strip() for c in rows[0].split("|")]


def test_dataset_version_none_is_the_default_render(tmp_path):
    out_default, _, _ = _render_two_versions(tmp_path / "a")
    out_none, _, _ = _render_two_versions(tmp_path / "b", dataset_version=None)
    assert out_default.name == "scorecard-dv-bank.md"
    assert out_default.read_bytes() == out_none.read_bytes()


def test_requesting_the_current_version_is_the_default_render(tmp_path):
    out_default, _, _ = _render_two_versions(tmp_path / "a")
    out_v2, rpt, _ = _render_two_versions(tmp_path / "b", dataset_version="v2")
    assert out_v2.name == "scorecard-dv-bank.md"
    assert out_default.read_bytes() == out_v2.read_bytes()
    assert not list(rpt.glob("*--*"))


def test_a_historical_version_is_written_to_its_own_file(tmp_path):
    out, rpt, caught = _render_two_versions(tmp_path, dataset_version="v1")
    assert out == rpt / "scorecard-dv-bank--v1.md"
    assert not (rpt / "scorecard-dv-bank.md").exists()
    content = out.read_text(encoding="utf-8")
    cols = _bare_rate_cols(content)
    assert cols[2:5] == ["4", "4", "100.0%"], cols
    first = content.splitlines()[0]
    assert "v1" in first
    assert "not the current" in first
    assert "v2" in first
    assert "tasks/" in first
    assert any("v2" in str(w.message) and "excluded" in str(w.message) for w in caught)


def test_a_historical_render_leaves_the_current_scorecard_alone(tmp_path):
    out_cur, rpt, _ = _render_two_versions(tmp_path)
    before = out_cur.read_bytes()
    ldgr = tmp_path / "ledger"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        render("dv-bank", ledger_dir=ldgr, report_dir=rpt, dataset_version="v1")
    assert out_cur.read_bytes() == before


def test_an_unknown_dataset_version_names_the_versions_in_the_ledger(tmp_path):
    ldgr = tmp_path / "ledger"
    ldgr.mkdir(parents=True)
    with open(ldgr / "dv-bank.jsonl", "w", encoding="utf-8") as f:
        for rec in _two_version_records():
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    with pytest.raises(ValueError) as exc:
        render("dv-bank", ledger_dir=ldgr, report_dir=tmp_path / "report", dataset_version="v9")
    msg = str(exc.value)
    assert "v9" in msg and "v1" in msg and "v2" in msg
    assert not (tmp_path / "report").exists()


def test_a_version_name_is_sanitized_in_the_file_name(tmp_path):
    ldgr = tmp_path / "ledger"
    ldgr.mkdir(parents=True)
    records = [_dv_trial("a/b c", "bare", "aaa", "task-x", 0, True)]
    records += [_dv_trial("z", "bare", "aaa", "task-x", 0, True)]
    with open(ldgr / "dv-bank.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = render(
            "dv-bank", ledger_dir=ldgr, report_dir=tmp_path / "report", dataset_version="a/b c"
        )
    assert out == tmp_path / "report" / "scorecard-dv-bank--a_b_c.md"


# ---------------------------------------------------------------------------
# --per-trial: USD, tokens, turns and wall time per (arm, task, repeat)
# ---------------------------------------------------------------------------


def _pt_trial(sc, ch, tid, rep, *, status="completed", dv="v1"):
    rec = _dv_trial(dv, sc, ch, tid, rep, True)
    rec["status"] = status
    return rec


def _pt_run(ch, tid, rep, *, usd, inp, out, turns, wall, source="reported", dv="v1"):
    rec = _dv_run(dv, "", ch, tid, rep)
    rec.update(
        cost_usd_est=usd,
        cost_source=source,
        usage={"input_tokens": inp, "output_tokens": out},
        turns=turns,
        duration=wall,
    )
    return rec


def _pt_ledger(tmp_path, records):
    ldgr = tmp_path / "ledger"
    ldgr.mkdir(parents=True, exist_ok=True)
    with open(ldgr / "dv-bank.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    return ldgr


def _pt_rows(tmp_path, records, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return per_trial_rows("dv-bank", _pt_ledger(tmp_path, records), **kwargs)


def test_per_trial_sums_the_run_rows_of_a_trial(tmp_path):
    records = [
        _pt_run("aaa", "add", 0, usd=0.10, inp=100, out=40, turns=3, wall=10.0),
        _pt_run("aaa", "add", 0, usd=0.25, inp=200, out=60, turns=5, wall=20.5),
        _pt_trial("bare", "aaa", "add", 0),
    ]
    (row,) = _pt_rows(tmp_path, records)
    assert (row.label, row.task_id, row.repeat, row.status, row.runs) == (
        "bare",
        "add",
        0,
        "completed",
        2,
    )
    assert row.usd == pytest.approx(0.35)
    assert (row.input_tokens, row.output_tokens, row.turns) == (300, 100, 8)
    assert row.wall == pytest.approx(30.5)
    assert row.usd_missing is False


def test_per_trial_keys_by_config_hash_not_arm_name(tmp_path):
    # FATH-B49: one arm name, two config hashes. The rows stay apart and say which is which.
    records = [
        _pt_run("aaa111111111", "add", 0, usd=0.10, inp=10, out=1, turns=1, wall=1.0),
        _pt_trial("bare", "aaa111111111", "add", 0),
        _pt_run("bbb222222222", "add", 0, usd=0.20, inp=20, out=2, turns=2, wall=2.0),
        _pt_trial("bare", "bbb222222222", "add", 0),
    ]
    rows = _pt_rows(tmp_path, records)
    assert [r.usd for r in rows] == [pytest.approx(0.10), pytest.approx(0.20)]
    assert [r.label for r in rows] == ["bare (aaa11111)", "bare (bbb22222)"]


def test_per_trial_label_is_the_bare_arm_name_when_one_hash_carries_it(tmp_path):
    records = [
        _pt_run("aaa", "add", 0, usd=0.1, inp=1, out=1, turns=1, wall=1.0),
        _pt_trial("bare", "aaa", "add", 0),
    ]
    (row,) = _pt_rows(tmp_path, records)
    assert row.label == "bare"


def test_per_trial_shows_the_status_of_an_errored_trial(tmp_path):
    records = [
        _pt_run("aaa", "add", 0, usd=0.1, inp=1, out=1, turns=1, wall=1.0),
        _pt_trial("bare", "aaa", "add", 0, status="errored"),
    ]
    (row,) = _pt_rows(tmp_path, records)
    assert row.status == "errored"
    assert "errored" in render_per_trial("dv-bank", [row])


def test_per_trial_marks_a_run_with_no_cost_reported(tmp_path):
    records = [
        _pt_run("aaa", "add", 0, usd=0.10, inp=1, out=1, turns=1, wall=1.0),
        _pt_run("aaa", "add", 0, usd=0.0, inp=1, out=1, turns=1, wall=1.0, source="none"),
        _pt_trial("bare", "aaa", "add", 0),
        _pt_run("aaa", "sub", 0, usd=0.30, inp=1, out=1, turns=1, wall=1.0),
        _pt_trial("bare", "aaa", "sub", 0),
    ]
    rows = _pt_rows(tmp_path, records)
    by_task = {r.task_id: r for r in rows}
    assert by_task["add"].usd_missing is True
    assert by_task["sub"].usd_missing is False
    table = render_per_trial("dv-bank", rows)
    add_line = next(ln for ln in table.splitlines() if "| add |" in ln)
    sub_line = next(ln for ln in table.splitlines() if "| sub |" in ln)
    assert "0.1000*" in add_line
    assert "0.3000*" not in sub_line and "0.3000" in sub_line
    assert "no cost" in table


def test_per_trial_a_trial_without_runs_is_a_row_of_zeros(tmp_path):
    (row,) = _pt_rows(tmp_path, [_pt_trial("bare", "aaa", "add", 0, status="errored")])
    assert (row.runs, row.usd, row.turns) == (0, 0.0, 0)


def test_per_trial_applies_voids_and_dataset_version_like_render(tmp_path):
    records = [
        _pt_run("aaa", "add", 0, usd=0.10, inp=1, out=1, turns=1, wall=1.0, dv="v1"),
        _pt_trial("bare", "aaa", "add", 0, dv="v1"),
        _pt_run("aaa", "add", 0, usd=0.50, inp=1, out=1, turns=1, wall=1.0, dv="v2"),
        _pt_trial("bare", "aaa", "add", 0, dv="v2"),
    ]
    (current,) = _pt_rows(tmp_path / "a", records)
    assert current.usd == pytest.approx(0.50)
    (old,) = _pt_rows(tmp_path / "b", records, dataset_version="v1")
    assert old.usd == pytest.approx(0.10)


def test_per_trial_table_has_a_header_and_one_line_per_trial(tmp_path):
    records = [
        _pt_run("aaa", "add", 0, usd=0.10, inp=1, out=1, turns=1, wall=1.0),
        _pt_trial("bare", "aaa", "add", 0),
    ]
    table = render_per_trial("dv-bank", _pt_rows(tmp_path, records))
    assert "| Arm | Task | Repeat | Status | Runs | Est. USD |" in table
    assert "| bare | add | 0 | completed | 1 | 0.1000 |" in table


def test_the_scorecard_and_golden_do_not_change(tmp_path):
    # Nothing in the scorecard path calls the per-trial view, and the golden still matches.
    out_a, _, _ = _render_two_versions(tmp_path / "a")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        per_trial_rows("dv-bank", tmp_path / "a" / "ledger")
    out_b, _, _ = _render_two_versions(tmp_path / "b")
    assert out_a.read_bytes() == out_b.read_bytes()


# ---------------------------------------------------------------------------
# Hard-criteria fraction: partial credit in the core scorecard, for every bank
# ---------------------------------------------------------------------------

_ALL_CRITERIA = "all criteria (no hard_criteria declared)"


def _hc_trial(sc, tid, rep, vr, *, status="completed", infra=False):
    return {
        "kind": "trial",
        "bank": "hc-bank",
        "task_id": tid,
        "repeat": rep,
        "status": status,
        "dataset_version": "v1",
        "config_hash": f"ch-{sc}",
        "verifier_results": vr,
        "scenario": sc,
        "holdout": False,
        "infra_error": infra,
    }


def _hc_tasks(tasks_dir: pathlib.Path, tasks: dict[str, list[str] | None]) -> None:
    """tasks/hc-bank/ with one task.toml per id; a list declares [verify] hard_criteria."""
    bank = tasks_dir / "hc-bank"
    bank.mkdir(parents=True)
    (bank / "bank.toml").write_text(
        'name = "hc-bank"\ndataset_version = "v1"\nholdout = []\n', encoding="utf-8"
    )
    for tid, hard in tasks.items():
        (bank / tid).mkdir()
        verify = 'entry = "verify.py"\n'
        if hard is not None:
            verify += f"hard_criteria = {json.dumps(hard)}\n"
        (bank / tid / "task.toml").write_text(
            f'id = "{tid}"\ninstruction = "x"\n[limits]\n[verify]\n{verify}', encoding="utf-8"
        )


def _hc_render(tmp_path, records, tasks: dict[str, list[str] | None] | None = None) -> str:
    ldgr = tmp_path / "ledger"
    ldgr.mkdir(parents=True)
    with open(ldgr / "hc-bank.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    tasks_dir = tmp_path / "tasks"
    if tasks is not None:
        _hc_tasks(tasks_dir, tasks)
    out = render("hc-bank", ledger_dir=ldgr, report_dir=tmp_path / "report", tasks_dir=tasks_dir)
    return out.read_text(encoding="utf-8")


def _hc_rows(content: str) -> dict[str, str]:
    """The Hard-Criteria Fraction rows of the first section, keyed by scenario."""
    lines = content.splitlines()
    start = lines.index("### Hard-Criteria Fraction")
    rows: dict[str, str] = {}
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        if line.startswith("| ") and not line.startswith("| Scenario"):
            rows[line.split("|")[1].strip()] = line
    return rows


def test_the_fraction_pools_criteria_over_an_arms_trials(tmp_path):
    # bare: 2 + 1 of 4 criteria true = 3/4; nudge: 4/4. No tasks/ tree, so every criterion counts.
    records = [
        _hc_trial("bare", "t1", 0, {"a": True, "b": True}),
        _hc_trial("bare", "t1", 1, {"a": True, "b": False}),
        _hc_trial("nudge", "t1", 0, {"a": True, "b": True}),
        _hc_trial("nudge", "t1", 1, {"a": True, "b": True}),
    ]
    content = _hc_render(tmp_path, records)
    rows = _hc_rows(content)
    assert rows["bare"] == f"| bare | 3/4 | 75.0% | {_ALL_CRITERIA} |"
    assert rows["nudge"] == f"| nudge | 4/4 | 100.0% | {_ALL_CRITERIA} |"
    assert "| Scenario | True / Present | Fraction | Criteria used |" in content


def test_the_fraction_table_follows_the_per_criterion_table(tmp_path):
    records = [_hc_trial("bare", "t1", 0, {"a": True, "b": False})]
    content = _hc_render(tmp_path, records)
    assert (
        content.index("### Per-Criterion Pass Rates")
        < content.index("### Hard-Criteria Fraction")
        < content.index("### Efficiency")
    )


def test_a_task_that_declares_hard_criteria_counts_only_those(tmp_path):
    # Only "a" is hard: r0 has a=True, r1 a=False, so 1/2 whatever "b" says.
    records = [
        _hc_trial("bare", "t1", 0, {"a": True, "b": False}),
        _hc_trial("bare", "t1", 1, {"a": False, "b": True}),
    ]
    content = _hc_render(tmp_path, records, tasks={"t1": ["a"]})
    assert _hc_rows(content)["bare"] == "| bare | 1/2 | 50.0% | hard_criteria |"


def test_an_arm_over_both_kinds_of_task_is_marked_mixed(tmp_path):
    # t1 declares ["a"] (1/1); t2 declares none, so both its criteria count (1/2): 2/3.
    records = [
        _hc_trial("bare", "t1", 0, {"a": True, "b": False}),
        _hc_trial("bare", "t2", 0, {"a": True, "b": False}),
    ]
    content = _hc_render(tmp_path, records, tasks={"t1": ["a"], "t2": None})
    assert _hc_rows(content)["bare"] == "| bare | 2/3 | 66.7% | mixed |"


def test_infra_and_errored_trials_are_left_out_of_the_fraction(tmp_path):
    records = [
        _hc_trial("bare", "t1", 0, {"a": True, "b": True}),
        _hc_trial("bare", "t1", 1, {"a": False, "b": False}, status="errored"),
        _hc_trial("bare", "t1", 2, {"a": False, "b": False}, infra=True),
    ]
    content = _hc_render(tmp_path, records)
    assert _hc_rows(content)["bare"] == f"| bare | 2/2 | 100.0% | {_ALL_CRITERIA} |"


def test_an_arm_whose_verifier_returned_no_criteria_reads_not_available(tmp_path):
    records = [_hc_trial("bare", "t1", 0, None), _hc_trial("nudge", "t1", 0, {"a": True})]
    content = _hc_render(tmp_path, records)
    assert _hc_rows(content)["bare"] == f"| bare | 0/0 | N/A | {_ALL_CRITERIA} |"


def test_a_historical_view_says_its_hard_criteria_are_the_current_ones(tmp_path):
    # The fraction of an older dataset_version still reads today's tasks/ tree.
    out, _, _ = _render_two_versions(tmp_path, dataset_version="v1")
    first = out.read_text(encoding="utf-8").splitlines()[0]
    assert "hard criteria" in first and "current tasks/ tree" in first


def test_hard_criteria_are_read_without_a_scores_file(tmp_path):
    from fathom.report import _load_task_criteria

    _hc_tasks(tmp_path / "tasks", {"t1": ["a", "b"], "t2": None})
    assert _load_task_criteria("hc-bank", tmp_path / "tasks") == {"t1": ["a", "b"], "t2": None}
    assert _load_task_criteria("other-bank", tmp_path / "tasks") == {}
    assert _load_task_criteria("hc-bank", tmp_path / "missing") == {}


def test_an_unreadable_bank_warns_and_counts_every_criterion(tmp_path):
    from fathom.report import _load_task_criteria

    (tmp_path / "tasks" / "hc-bank").mkdir(parents=True)  # no bank.toml
    with pytest.warns(UserWarning, match="hard_criteria"):
        assert _load_task_criteria("hc-bank", tmp_path / "tasks") == {}


_CALIBRATION_SECTION = _FIXTURES_DIR / "calibration-section.md"


def _calibration_bank_scorecard(tmp_path: pathlib.Path) -> str:
    """The scorecard of a calibration bank: scores.toml, hard_criteria, three tiered arms."""
    bank = tmp_path / "tasks" / "cal"
    for tid, hard in (("t1", ["correctness"]), ("t2", ["correctness", "style"])):
        (bank / tid).mkdir(parents=True)
        (bank / tid / "task.toml").write_text(
            f'id = "{tid}"\ninstruction = "x"\n[limits]\n'
            f'[verify]\nentry = "verify.py"\nhard_criteria = {json.dumps(hard)}\n',
            encoding="utf-8",
        )
    (bank / "bank.toml").write_text(
        'name = "cal"\ndataset_version = "1"\nholdout = []\n', encoding="utf-8"
    )
    (bank / "scores.toml").write_text("[scores]\nt1 = 10\nt2 = 80\n", encoding="utf-8")
    passes = {"haiku": (True, False), "sonnet": (True, False), "opus": (True, True)}
    records: list[dict] = []
    for arm, (t1_pass, t2_pass) in passes.items():
        for tid, ok in (("t1", t1_pass), ("t2", t2_pass)):
            for rep in range(2):
                run = _dv_run("1", arm, f"ch-{arm}", tid, rep)
                run["bank"] = "cal"
                trial = _dv_trial("1", arm, f"ch-{arm}", tid, rep, ok)
                trial["bank"] = "cal"
                trial["verifier_results"] = {"correctness": ok, "style": ok, "extra": not ok}
                records += [run, trial]
    ldgr = tmp_path / "ledger"
    ldgr.mkdir()
    with open(ldgr / "cal.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    out = render(
        "cal", ledger_dir=ldgr, report_dir=tmp_path / "report", tasks_dir=tmp_path / "tasks"
    )
    return out.read_text(encoding="utf-8")


def test_the_calibration_section_is_unchanged_by_the_fraction(tmp_path):
    # The snapshot was taken before the core scorecard gained the fraction table.
    content = _calibration_bank_scorecard(tmp_path)
    section = content[content.index("## Model-Tier Calibration") :]
    assert section == _CALIBRATION_SECTION.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Task tags: a per-tag grouping of the pass rates when the bank declares tags
# ---------------------------------------------------------------------------


def _tag_tasks(tasks_dir: pathlib.Path, tags: dict[str, dict[str, str] | None]) -> None:
    """tasks/hc-bank/ with one task.toml per id; a dict declares that task's [tags]."""
    bank = tasks_dir / "hc-bank"
    bank.mkdir(parents=True)
    (bank / "bank.toml").write_text(
        'name = "hc-bank"\ndataset_version = "v1"\nholdout = []\n', encoding="utf-8"
    )
    for tid, declared in tags.items():
        (bank / tid).mkdir()
        body = f'id = "{tid}"\ninstruction = "x"\n[limits]\n[verify]\nentry = "verify.py"\n'
        if declared is not None:
            body += "[tags]\n" + "".join(f'{k} = "{v}"\n' for k, v in declared.items())
        (bank / tid / "task.toml").write_text(body, encoding="utf-8")


def _tag_records() -> list[dict]:
    # t1: bare 1/2, nudge 2/2.  t2: bare 0/2, nudge 1/2.  t3: bare 1/1, nudge 1/1.
    ok, bad = {"a": True}, {"a": False}
    return [
        _hc_trial("bare", "t1", 0, ok),
        _hc_trial("bare", "t1", 1, bad),
        _hc_trial("nudge", "t1", 0, ok),
        _hc_trial("nudge", "t1", 1, ok),
        _hc_trial("bare", "t2", 0, bad),
        _hc_trial("bare", "t2", 1, bad),
        _hc_trial("nudge", "t2", 0, ok),
        _hc_trial("nudge", "t2", 1, bad),
        _hc_trial("bare", "t3", 0, ok),
        _hc_trial("nudge", "t3", 0, ok),
    ]


def _tag_render(tmp_path, tags: dict[str, dict[str, str] | None]) -> str:
    ldgr = tmp_path / "ledger"
    ldgr.mkdir(parents=True)
    with open(ldgr / "hc-bank.jsonl", "w", encoding="utf-8") as f:
        for rec in _tag_records():
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    tasks_dir = tmp_path / "tasks"
    _tag_tasks(tasks_dir, tags)
    out = render("hc-bank", ledger_dir=ldgr, report_dir=tmp_path / "report", tasks_dir=tasks_dir)
    return out.read_text(encoding="utf-8")


def _tag_table(content: str, key: str) -> list[str]:
    lines = content.splitlines()
    start = lines.index(f"### By tag: {key}")
    table: list[str] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        table.append(line)
    return table


def test_a_tagged_bank_renders_a_per_tag_table_with_per_arm_counts(tmp_path):
    content = _tag_render(tmp_path, {"t1": {"size": "small"}, "t2": {"size": "large"}, "t3": None})
    assert _tag_table(content, "size") == [
        "| size | bare | nudge |",
        "|---|---|---|",
        "| large | 0/2 (0.0%) | 1/2 (50.0%) |",
        "| small | 1/2 (50.0%) | 2/2 (100.0%) |",
        "| (untagged) | 1/1 (100.0%) | 1/1 (100.0%) |",
    ]


def test_each_tag_key_gets_its_own_table_after_the_verdicts(tmp_path):
    content = _tag_render(
        tmp_path,
        {"t1": {"size": "small", "kind": "fix"}, "t2": {"size": "large"}, "t3": None},
    )
    assert (
        content.index("### Verdicts")
        < content.index("### By tag: kind")
        < content.index("### By tag: size")
        < content.index("### Per-Criterion Pass Rates")
    )
    # t2 and t3 carry no kind, so both are untagged for that key.
    assert _tag_table(content, "kind")[2:] == [
        "| fix | 1/2 (50.0%) | 2/2 (100.0%) |",
        "| (untagged) | 1/3 (33.3%) | 2/3 (66.7%) |",
    ]


def test_a_bank_that_declares_no_tags_has_no_tag_table(tmp_path):
    content = _tag_render(tmp_path, {"t1": None, "t2": None, "t3": None})
    assert "By tag" not in content


def test_a_tag_value_with_no_trials_in_the_section_is_not_listed(tmp_path):
    # t9 declares size=huge but has no trials, so it never reaches the table.
    tags = {
        "t1": {"size": "small"},
        "t2": {"size": "small"},
        "t3": {"size": "small"},
        "t9": {"size": "huge"},
    }
    content = _tag_render(tmp_path, tags)
    assert _tag_table(content, "size")[2:] == ["| small | 2/5 (40.0%) | 4/5 (80.0%) |"]


def test_task_tags_are_read_without_a_scores_file(tmp_path):
    from fathom.report import _load_task_tags

    _tag_tasks(tmp_path / "tasks", {"t1": {"size": "small"}, "t2": None})
    assert _load_task_tags("hc-bank", tmp_path / "tasks") == {"t1": {"size": "small"}, "t2": {}}
    assert _load_task_tags("other-bank", tmp_path / "tasks") == {}
    assert _load_task_tags("hc-bank", tmp_path / "missing") == {}


# ---------------------------------------------------------------------------
# Arm Health: MCP calls, counted from the kept streams of arms that mount a plugin
# ---------------------------------------------------------------------------

_STREAM_FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "streams"
_MOUNT = json.dumps(
    {"name": "x", "plugins": [{"name": "example", "tree_sha": "t", "version": "1.0.0"}]},
    sort_keys=True,
)
_NO_MOUNT = json.dumps({"name": "x"}, sort_keys=True)
_MCP_HEADING = "### Arm Health: MCP calls"


def _mcp_trial(sc, tid, rep, *, preimage=_MOUNT, status="completed"):
    rec = _hc_trial(sc, tid, rep, {"a": True}, status=status)
    rec["bank"] = "mcp-bank"
    if preimage is not None:
        rec["config_preimage"] = preimage
    return rec


def _keep(streams_dir, sc, tid, rep, *fixtures):
    """Copy fixture streams to the names the adapter tees for that trial, one per spawn."""
    streams_dir.mkdir(parents=True, exist_ok=True)
    for n, name in enumerate(fixtures, 1):
        body = (_STREAM_FIXTURES / name).read_text(encoding="utf-8")
        target = streams_dir / f"mcp-bank--{sc}--{tid}--r{rep}--a1--{1000 + n}.ndjson"
        target.write_text(body, encoding="utf-8")


def _mcp_ledger(tmp_path, records) -> pathlib.Path:
    ldgr = tmp_path / "ledger"
    ldgr.mkdir(parents=True, exist_ok=True)
    with open(ldgr / "mcp-bank.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    return ldgr


def _mcp_render(tmp_path, records, streams_dir=None) -> str:
    out = render(
        "mcp-bank",
        ledger_dir=_mcp_ledger(tmp_path, records),
        report_dir=tmp_path / "report",
        tasks_dir=tmp_path / "tasks",
        streams_dir=tmp_path / "streams" if streams_dir is None else streams_dir,
    )
    return out.read_text(encoding="utf-8")


def _mcp_table(content: str) -> list[str]:
    lines = content.splitlines()
    start = lines.index(_MCP_HEADING)
    table: list[str] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        table.append(line)
    return table


def test_mcp_calls_render_served_denied_partial_and_missing(tmp_path):
    streams_dir = tmp_path / "streams"
    _keep(streams_dir, "served", "t1", 0, "served.ndjson")
    _keep(streams_dir, "denied", "t1", 0, "denied.ndjson")
    _keep(streams_dir, "cut", "t1", 0, "truncated.ndjson")
    _keep(streams_dir, "bare", "t1", 0, "served.ndjson")
    records = [
        _mcp_trial("served", "t1", 0),
        _mcp_trial("denied", "t1", 0),
        _mcp_trial("cut", "t1", 0),
        _mcp_trial("unkept", "t1", 0),
        _mcp_trial("bare", "t1", 0, preimage=_NO_MOUNT),
    ]
    assert _mcp_table(_mcp_render(tmp_path, records)) == [
        "| Scenario | Trials with streams | MCP calls per trial (min/med/max) | Flag |",
        "|---|---|---|---|",
        "| cut | 1/1 | 1/1/1 (1 partial) |  |",
        "| denied | 1/1 | 0/0/0 | all calls denied or absent |",
        "| served | 1/1 | 1/1/1 |  |",
        "| unkept | 0/1 | no streams kept |  |",
    ]


def test_a_trials_count_sums_its_stream_files(tmp_path):
    # r1 spawned twice (two files), each with one served call; r2's call was denied.
    streams_dir = tmp_path / "streams"
    _keep(streams_dir, "nudge", "t1", 0, "served.ndjson")
    _keep(streams_dir, "nudge", "t1", 1, "served.ndjson", "served.ndjson")
    _keep(streams_dir, "nudge", "t1", 2, "denied.ndjson")
    records = [_mcp_trial("nudge", "t1", rep) for rep in range(3)]
    assert _mcp_table(_mcp_render(tmp_path, records))[2:] == ["| nudge | 3/3 | 0/1/2 |  |"]


def test_the_flag_needs_every_trial_with_streams_at_zero(tmp_path):
    streams_dir = tmp_path / "streams"
    _keep(streams_dir, "quiet", "t1", 0, "denied.ndjson")
    _keep(streams_dir, "mixed", "t1", 0, "denied.ndjson")
    _keep(streams_dir, "mixed", "t1", 1, "served.ndjson")
    records = [
        _mcp_trial("quiet", "t1", 0),
        _mcp_trial("quiet", "t1", 1),  # no stream kept: not counted as a zero
        _mcp_trial("mixed", "t1", 0),
        _mcp_trial("mixed", "t1", 1),
    ]
    assert _mcp_table(_mcp_render(tmp_path, records))[2:] == [
        "| mixed | 2/2 | 0/0/1 |  |",
        "| quiet | 1/2 | 0/0/0 | all calls denied or absent |",
    ]


def test_a_call_to_a_server_the_spawn_did_not_report_is_not_counted(tmp_path):
    # A successful mcp__ call whose server is not in the init event's mcp_servers.
    body = (_STREAM_FIXTURES / "served.ndjson").read_text(encoding="utf-8")
    streams_dir = tmp_path / "streams"
    streams_dir.mkdir()
    name = "mcp-bank--served--t1--r0--a1--1001.ndjson"
    (streams_dir / name).write_text(body.replace("mcp__srv__x", "mcp__other__x"), encoding="utf-8")
    table = _mcp_table(_mcp_render(tmp_path, [_mcp_trial("served", "t1", 0)]))
    assert table[2:] == ["| served | 1/1 | 0/0/0 | all calls denied or absent |"]


def test_errored_and_infra_trials_are_not_counted(tmp_path):
    streams_dir = tmp_path / "streams"
    _keep(streams_dir, "served", "t1", 0, "served.ndjson")
    _keep(streams_dir, "served", "t1", 1, "served.ndjson")
    infra = _mcp_trial("served", "t1", 2)
    infra["infra_error"] = True
    records = [
        _mcp_trial("served", "t1", 0),
        _mcp_trial("served", "t1", 1, status="errored"),
        infra,
    ]
    assert _mcp_table(_mcp_render(tmp_path, records))[2:] == ["| served | 1/1 | 1/1/1 |  |"]


def test_a_ledger_without_a_mount_arm_renders_no_mcp_table(tmp_path):
    # Streams are kept for both arms, but neither mounts a plugin (one row is legacy).
    streams_dir = tmp_path / "streams"
    _keep(streams_dir, "bare", "t1", 0, "served.ndjson")
    _keep(streams_dir, "old", "t1", 0, "served.ndjson")
    records = [
        _mcp_trial("bare", "t1", 0, preimage=_NO_MOUNT),
        _mcp_trial("old", "t1", 0, preimage=None),
    ]
    with_streams = _mcp_render(tmp_path / "a", records, streams_dir=streams_dir)
    without = _mcp_render(tmp_path / "b", records, streams_dir=tmp_path / "missing")
    assert "MCP calls" not in with_streams
    assert with_streams == without


def test_legacy_rows_without_a_preimage_are_left_out_and_the_note_names_them(tmp_path):
    streams_dir = tmp_path / "streams"
    _keep(streams_dir, "served", "t1", 0, "served.ndjson")
    _keep(streams_dir, "old", "t1", 0, "served.ndjson")
    records = [_mcp_trial("served", "t1", 0), _mcp_trial("old", "t1", 0, preimage=None)]
    content = _mcp_render(tmp_path, records)
    assert _mcp_table(content)[2:] == ["| served | 1/1 | 1/1/1 |  |"]
    after = content[content.index(_MCP_HEADING) :]
    assert "Left out: the trials of old" in after
    assert "config_preimage" in after


def test_the_mcp_note_states_that_reruns_of_a_cell_share_a_stream_name(tmp_path):
    _keep(tmp_path / "streams", "served", "t1", 0, "served.ndjson")
    content = _mcp_render(tmp_path, [_mcp_trial("served", "t1", 0)])
    after = content[content.index(_MCP_HEADING) :]
    assert "share a stream name" in after
    assert "Left out" not in after


def test_the_mcp_table_follows_economy_and_precedes_efficiency(tmp_path):
    _keep(tmp_path / "streams", "served", "t1", 0, "served.ndjson")
    run = _dv_run("v1", "served", "ch-served", "t1", 0)
    content = _mcp_render(tmp_path, [run, _mcp_trial("served", "t1", 0)])
    assert content.index("### Economy") < content.index(_MCP_HEADING)
    assert content.index(_MCP_HEADING) < content.index("### Efficiency")


def test_the_default_streams_dir_is_fathom_stream_dir_then_the_data_root(tmp_path, monkeypatch):
    from fathom.cli import _default_stream_dir

    ldgr = _mcp_ledger(tmp_path, [_mcp_trial("served", "t1", 0)])

    def _rendered() -> list[str]:
        out = render("mcp-bank", ledger_dir=ldgr, report_dir=tmp_path / "report")
        return _mcp_table(out.read_text(encoding="utf-8"))[2:]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FATHOM_STREAM_DIR", str(tmp_path / "elsewhere"))
    _keep(tmp_path / "elsewhere", "served", "t1", 0, "served.ndjson")
    assert _rendered() == ["| served | 1/1 | 1/1/1 |  |"]

    monkeypatch.delenv("FATHOM_STREAM_DIR")
    assert _rendered() == ["| served | 0/1 | no streams kept |  |"]
    assert _default_stream_dir("mcp-bank") == tmp_path / ".fathom" / "streams" / "mcp-bank"
    _keep(_default_stream_dir("mcp-bank"), "served", "t1", 0, "denied.ndjson")
    assert _rendered() == ["| served | 1/1 | 0/0/0 | all calls denied or absent |"]


def test_a_stream_the_adapter_tees_is_found_by_its_trial(tmp_path, monkeypatch):
    # The adapter names the file after the tag the run loop sets, replacing characters it
    # does not keep; the report must find it under the arm name the ledger records.
    from fathom.adapters.claude_cli import ClaudeCliRunner

    streams_dir = tmp_path / "streams"
    monkeypatch.setenv("FATHOM_STREAM_DIR", str(streams_dir))
    monkeypatch.setenv("FATHOM_STREAM_TAG", "mcp-bank--with mcp+--t1--r0")
    body = (_STREAM_FIXTURES / "served.ndjson").read_text(encoding="utf-8")
    ClaudeCliRunner._tee_stream(body, 1, 1.0)
    assert len(list(streams_dir.glob("*.ndjson"))) == 1
    table = _mcp_table(_mcp_render(tmp_path, [_mcp_trial("with mcp+", "t1", 0)]))
    assert table[2:] == ["| with mcp+ | 1/1 | 1/1/1 |  |"]


# ---------------------------------------------------------------------------
# Contrasts: bank-declared treatment/control pairs, one-sided Fisher, Wilson and Holm
# ---------------------------------------------------------------------------

_CONTRASTS_HEADING = "### Contrasts"


def _hypergeometric_left_tail(control_pass, n_control, treatment_pass, n_treatment) -> float:
    """P(control passes <= control_pass) given both margins: the exact one-sided Fisher p for
    "the treatment passes more often", summed term by term."""
    from math import comb

    total, passes = n_control + n_treatment, control_pass + treatment_pass
    return sum(
        comb(passes, k) * comb(total - passes, n_control - k)
        for k in range(max(0, passes - n_treatment), control_pass + 1)
    ) / comb(total, n_control)


def _ct_trials(sc: str, n: int, passes: int, *, vr_pass=None, vr_fail=None) -> list[dict]:
    """*n* completed trials of arm *sc* on task t1, the first *passes* of them passing."""
    ok = {"a": True} if vr_pass is None else vr_pass
    bad = {"a": False} if vr_fail is None else vr_fail
    return [_hc_trial(sc, "t1", rep, ok if rep < passes else bad) for rep in range(n)]


def _ct_render(tmp_path, records, contrasts_toml: str | None) -> str:
    """Render hc-bank with a bank.toml that carries *contrasts_toml* after its three keys."""
    bank = tmp_path / "tasks" / "hc-bank"
    bank.mkdir(parents=True)
    manifest = 'name = "hc-bank"\ndataset_version = "v1"\nholdout = []\n'
    (bank / "bank.toml").write_text(manifest + (contrasts_toml or ""), encoding="utf-8")
    ldgr = tmp_path / "ledger"
    ldgr.mkdir(parents=True)
    with open(ldgr / "hc-bank.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    out = render(
        "hc-bank", ledger_dir=ldgr, report_dir=tmp_path / "report", tasks_dir=tmp_path / "tasks"
    )
    return out.read_text(encoding="utf-8")


def _ct_block(content: str) -> list[str]:
    """The first section's Contrasts block, heading excluded, up to the next heading."""
    lines = content.splitlines()
    start = lines.index(_CONTRASTS_HEADING)
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        block.append(line)
    return block


def _ct_rows(content: str) -> list[list[str]]:
    """The Contrasts table's data rows, split into stripped cells."""
    rows = [line for line in _ct_block(content) if line.startswith("| ")]
    return [[cell.strip() for cell in row.split("|")[1:-1]] for row in rows[1:]]


def _arm_cell(passes: int, n: int) -> str:
    lo, hi = wilson_interval(passes, n)
    return f"{passes}/{n} ({100 * passes / n:.1f}%) [{100 * lo:.1f}%, {100 * hi:.1f}%]"


_PAIR = '[[contrasts.pair]]\ntreatment = "{t}"\ncontrol = "{c}"\n'


def test_a_contrast_reproduces_the_exact_one_sided_fisher_p(tmp_path):
    records = _ct_trials("nudge", 10, 8) + _ct_trials("bare", 10, 2)
    content = _ct_render(tmp_path, records, _PAIR.format(t="nudge", c="bare"))
    p = _hypergeometric_left_tail(2, 10, 8, 10)
    assert abs(p - 0.0115) < 0.0001
    assert _ct_rows(content) == [
        [
            "nudge vs bare",
            "all criteria",
            _arm_cell(8, 10),
            _arm_cell(2, 10),
            f"{p:.4f}",
            "0.0500",
            "yes",
        ]
    ]
    header = next(line for line in _ct_block(content) if line.startswith("| "))
    assert header == (
        "| Treatment vs control | Criterion | Treatment | Control | Fisher p (one-sided)"
        " | Holm threshold | Below threshold |"
    )


def test_holm_thresholds_step_down_in_p_order(tmp_path):
    # Declared out of p order. strong 9/10 vs bare 2/10 has the smallest p, mid 7/10 vs bare
    # the next, late 8/12 vs early 3/12 the largest. The thresholds in p order are 0.05/3,
    # 0.05/2 and 0.05. mid misses its threshold, so late is not below its own even though
    # its p is under 0.05: the step-down stops at the first miss.
    records = (
        _ct_trials("bare", 10, 2)
        + _ct_trials("strong", 10, 9)
        + _ct_trials("mid", 10, 7)
        + _ct_trials("late", 12, 8)
        + _ct_trials("early", 12, 3)
    )
    declared = "".join(
        _PAIR.format(t=t, c=c) for t, c in [("late", "early"), ("mid", "bare"), ("strong", "bare")]
    )
    content = _ct_render(tmp_path, records, declared)
    p_strong = _hypergeometric_left_tail(2, 10, 9, 10)
    p_mid = _hypergeometric_left_tail(2, 10, 7, 10)
    p_late = _hypergeometric_left_tail(3, 12, 8, 12)
    assert p_strong < 0.05 / 3 < p_mid and 0.05 / 2 < p_mid < p_late < 0.05
    rows = _ct_rows(content)
    assert [r[0] for r in rows] == ["strong vs bare", "mid vs bare", "late vs early"]
    assert [r[4] for r in rows] == [f"{p:.4f}" for p in (p_strong, p_mid, p_late)]
    assert [r[5] for r in rows] == [f"{0.05 / 3:.4f}", f"{0.05 / 2:.4f}", f"{0.05:.4f}"]
    assert [r[6] for r in rows] == ["yes", "no", "no"]


def test_a_declared_alpha_sets_the_holm_thresholds(tmp_path):
    records = _ct_trials("nudge", 10, 8) + _ct_trials("bare", 10, 2) + _ct_trials("add", 10, 3)
    declared = "[contrasts]\nalpha = 0.1\n" + "".join(
        _PAIR.format(t=t, c="bare") for t in ("nudge", "add")
    )
    content = _ct_render(tmp_path, records, declared)
    rows = _ct_rows(content)
    assert [(r[0], r[5]) for r in rows] == [("nudge vs bare", "0.0500"), ("add vs bare", "0.1000")]
    assert "α = 0.1" in "\n".join(_ct_block(content))


def test_a_criterion_pair_counts_that_criterion(tmp_path):
    # Every trial fails criterion a, so the all-criteria pass is 0/10 for both arms; on
    # criterion b, nudge passes 8 of 10 and bare 2 of 10.
    hit, miss = {"a": False, "b": True}, {"a": False, "b": False}
    records = _ct_trials("nudge", 10, 8, vr_pass=hit, vr_fail=miss) + _ct_trials(
        "bare", 10, 2, vr_pass=hit, vr_fail=miss
    )
    declared = (
        _PAIR.format(t="nudge", c="bare") + 'criterion = "b"\n' + _PAIR.format(t="nudge", c="bare")
    )
    rows = _ct_rows(_ct_render(tmp_path, records, declared))
    by_criterion = {r[1]: r for r in rows}
    assert by_criterion["b"][2:5] == [
        _arm_cell(8, 10),
        _arm_cell(2, 10),
        f"{_hypergeometric_left_tail(2, 10, 8, 10):.4f}",
    ]
    assert by_criterion["all criteria"][2:5] == [
        _arm_cell(0, 10),
        _arm_cell(0, 10),
        f"{_hypergeometric_left_tail(0, 10, 0, 10):.4f}",
    ]


def test_a_bank_toml_without_contrasts_renders_the_golden_scorecard(tmp_path):
    bank = tmp_path / "tasks" / "test-bank"
    bank.mkdir(parents=True)
    (bank / "bank.toml").write_text(
        'name = "test-bank"\ndataset_version = "v1"\nholdout = []\n', encoding="utf-8"
    )
    _write_fixture(tmp_path / "ledger", "test-bank")
    with_manifest = render(
        "test-bank",
        ledger_dir=tmp_path / "ledger",
        report_dir=tmp_path / "with-manifest",
        tasks_dir=tmp_path / "tasks",
    )
    without_tasks = render(
        "test-bank",
        ledger_dir=tmp_path / "ledger",
        report_dir=tmp_path / "without-tasks",
        tasks_dir=tmp_path / "no-tasks",
    )
    assert with_manifest.read_bytes() == without_tasks.read_bytes()
    assert with_manifest.read_text(encoding="utf-8") == _GOLDEN.read_text(encoding="utf-8")


def test_a_pair_naming_an_unknown_arm_gets_a_note_line(tmp_path):
    records = _ct_trials("nudge", 10, 8) + _ct_trials("bare", 10, 2)
    declared = _PAIR.format(t="ghost", c="bare") + _PAIR.format(t="nudge", c="bare")
    content = _ct_render(tmp_path, records, declared)
    assert "> Not compared: ghost vs bare. The ledger has no arm named ghost." in _ct_block(content)
    rows = _ct_rows(content)
    assert [r[0] for r in rows] == ["nudge vs bare"]
    assert rows[0][5] == "0.0500"  # the family is the one pair that was compared


def test_an_arm_without_trials_in_the_section_is_left_out_of_the_family(tmp_path):
    # add has trials only on a holdout task, so in the dev section it has none.
    holdout = _hc_trial("add", "h1", 0, {"a": True})
    holdout["holdout"] = True
    records = _ct_trials("nudge", 10, 8) + _ct_trials("bare", 10, 2) + [holdout]
    declared = _PAIR.format(t="add", c="bare") + _PAIR.format(t="nudge", c="bare")
    rows = _ct_rows(_ct_render(tmp_path, records, declared))
    assert [r[0] for r in rows] == ["nudge vs bare", "add vs bare"]
    assert rows[0][5:] == ["0.0500", "yes"]
    assert rows[1] == ["add vs bare", "all criteria", "0/0", _arm_cell(2, 10), "N/A", "—", "—"]


def test_the_contrasts_block_follows_the_fraction_and_carries_a_neutral_note(tmp_path):
    records = _ct_trials("nudge", 10, 8) + _ct_trials("bare", 10, 2)
    content = _ct_render(tmp_path, records, _PAIR.format(t="nudge", c="bare"))
    assert content.index("### Hard-Criteria Fraction") < content.index(_CONTRASTS_HEADING)
    assert content.index(_CONTRASTS_HEADING) < content.index("### Efficiency")
    note = " ".join(line for line in _ct_block(content) if line.startswith(">"))
    assert "`[contrasts]`" in note and "Wilson 95%" in note and "directional" in note


def test_a_malformed_pair_warns_and_is_skipped(tmp_path):
    records = _ct_trials("nudge", 10, 8) + _ct_trials("bare", 10, 2)
    declared = '[[contrasts.pair]]\ntreatment = "nudge"\n' + _PAIR.format(t="nudge", c="bare")
    with pytest.warns(UserWarning, match=r"contrasts\.pair 1 .*control"):
        content = _ct_render(tmp_path, records, declared)
    assert [r[0] for r in _ct_rows(content)] == ["nudge vs bare"]


def test_an_alpha_outside_zero_and_one_warns_and_renders_no_contrasts(tmp_path):
    records = _ct_trials("nudge", 10, 8) + _ct_trials("bare", 10, 2)
    declared = "[contrasts]\nalpha = 5\n" + _PAIR.format(t="nudge", c="bare")
    with pytest.warns(UserWarning, match="alpha"):
        content = _ct_render(tmp_path, records, declared)
    assert _CONTRASTS_HEADING not in content


@pytest.mark.parametrize(
    ("declared", "message"),
    [
        ("contrasts = 3\n", "contrasts must be a table"),
        ('[[contrasts.pair]]\ntreatment = "nudge"\ncontrol = "bare"\ncriterion = 3\n', "criterion"),
    ],
)
def test_a_declaration_of_the_wrong_type_warns_instead_of_failing(tmp_path, declared, message):
    records = _ct_trials("nudge", 10, 8) + _ct_trials("bare", 10, 2)
    with pytest.warns(UserWarning, match=message):
        content = _ct_render(tmp_path, records, declared)
    assert _CONTRASTS_HEADING not in content


# ---------------------------------------------------------------------------
# The replication line under the title: the bank's [plan] repeats_per_cell against the cells
# ---------------------------------------------------------------------------


def _plan_line(content: str) -> list[str]:
    """The non-blank lines between the title and the first section heading."""
    lines = content.splitlines()
    title = next(i for i, line in enumerate(lines) if line.startswith("# Scorecard"))
    end = next(i for i, line in enumerate(lines) if i > title and line.startswith("## "))
    return [line for line in lines[title + 1 : end] if line.strip()]


def test_an_undeclared_plan_opens_the_scorecard_with_a_directional_line(tmp_path):
    content = _ct_render(tmp_path, _ct_trials("bare", 3, 2), None)
    lines = content.splitlines()
    assert lines[0] == "# Scorecard — hc-bank"
    assert lines[1] == ""
    assert lines[2].startswith("> **Directional:** ")
    assert "repeats_per_cell" in lines[2]
    assert lines[2].endswith("every verdict and contrast below is directional, not replicated.")
    assert lines[3] == ""
    assert lines[4].startswith("## ")


def test_a_plan_of_one_is_directional(tmp_path):
    content = _ct_render(tmp_path, _ct_trials("bare", 3, 2), "[plan]\nrepeats_per_cell = 1\n")
    (line,) = _plan_line(content)
    assert line.startswith("> **Directional:** ")
    assert "1 repeat" in line


def test_a_cell_below_the_plan_is_directional_and_counted(tmp_path):
    records = _ct_trials("bare", 3, 2) + _ct_trials("nudge", 2, 2)
    content = _ct_render(tmp_path, records, "[plan]\nrepeats_per_cell = 3\n")
    (line,) = _plan_line(content)
    assert line.startswith("> **Directional:** 1 of 2 arm x task cells")
    assert "repeats_per_cell = 3" in line


def test_a_cell_counts_completed_trials_only(tmp_path):
    records = _ct_trials("bare", 3, 2)
    records[2] = _hc_trial("bare", "t1", 2, None, status="errored")
    content = _ct_render(tmp_path, records, "[plan]\nrepeats_per_cell = 3\n")
    (line,) = _plan_line(content)
    assert line.startswith("> **Directional:** 1 of 1 arm x task cells")


def test_a_met_plan_says_so_without_the_directional_mark(tmp_path):
    records = _ct_trials("bare", 3, 2) + _ct_trials("nudge", 4, 2)
    content = _ct_render(tmp_path, records, "[plan]\nrepeats_per_cell = 3\n")
    (line,) = _plan_line(content)
    assert not line.startswith(">")
    assert "irectional" not in line
    assert "repeats_per_cell = 3" in line


def test_a_malformed_plan_warns_and_reads_as_undeclared(tmp_path):
    with pytest.warns(UserWarning, match=r"\[plan\]"):
        content = _ct_render(tmp_path, _ct_trials("bare", 3, 2), "[plan]\nrepeats_per_cell = 0\n")
    (line,) = _plan_line(content)
    assert line.startswith("> **Directional:** ")
    assert "malformed" in line


def test_the_plan_line_holds_the_version_the_view_renders(tmp_path):
    # v1 holds three completed trials of bare; the current v2 holds one.
    bank = tmp_path / "tasks" / "hc-bank"
    bank.mkdir(parents=True)
    (bank / "bank.toml").write_text(
        'name = "hc-bank"\ndataset_version = "v2"\nholdout = []\n[plan]\nrepeats_per_cell = 3\n',
        encoding="utf-8",
    )
    records = [
        *_ct_trials("bare", 3, 3),
        {**_hc_trial("bare", "t1", 0, {"a": True}), "dataset_version": "v2"},
    ]
    ldgr = tmp_path / "ledger"
    ldgr.mkdir()
    (ldgr / "hc-bank.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8"
    )
    tasks = tmp_path / "tasks"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        current = render("hc-bank", ledger_dir=ldgr, report_dir=tmp_path / "r", tasks_dir=tasks)
        old = render(
            "hc-bank",
            ledger_dir=ldgr,
            report_dir=tmp_path / "r",
            tasks_dir=tasks,
            dataset_version="v1",
        )
    assert _plan_line(current.read_text(encoding="utf-8"))[0].startswith("> **Directional:** ")
    old_lines = _plan_line(old.read_text(encoding="utf-8"))
    assert not old_lines[-1].startswith(">"), old_lines
    assert "repeats_per_cell = 3" in old_lines[-1]


def test_the_verdict_suffix_is_unchanged(tmp_path):
    records = _ct_trials("bare", 3, 2) + _ct_trials("nudge", 4, 2)
    content = _ct_render(tmp_path, records, "[plan]\nrepeats_per_cell = 3\n")
    assert "— directional, not final" in content
