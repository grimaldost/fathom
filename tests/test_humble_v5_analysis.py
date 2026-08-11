"""Guards for `scripts-humble-v5/analysis.py` and the numbers V5_NOTES pre-registers.

Two jobs.

**The tool works.** `analysis.py spend` is the only cumulative budget rail this bank has —
fathom's `--max-budget-usd` is a per-spawn cap and its run loop never halts on money
already spent. A spend rail that miscounts, or that fails to exit non-zero at the
threshold, is worse than none, because the operator is relying on it while chunking a paid
matrix. The `criteria`/`cost` paths are the pre-registered analysis, which exists because
`fathom report` pools criteria across tasks.

**The published numbers stay true.** `V5_NOTES.md` forecasts spend, sizes gate 3 and
declares the bank's ceilings from the *committed v1 and v2 ledgers*. Those claims decide
whether real money is spent, so they are recomputed here rather than trusted as prose. If
a ledger is ever archived or amended, these fail and the notes get corrected with it.

`python tests/test_humble_v5_analysis.py` runs without uv and without credentials.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import statistics
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).parent.parent
SCRIPT = REPO / "scripts-humble-v5" / "analysis.py"
LEDGER_DIR = REPO / "ledger"

# The Opus 4.8 -> Opus 5 scaling used by the V5_NOTES forecast (2026-08-11 recalibration).
OPUS5_FACTOR = 1.40
TRIALS_PER_ARM_AT_N20 = 80

V5_TASKS = (
    "feature-csv-coalesce",
    "feature-retry-backoff",
    "fix-offbyone-paginator",
    "fix-tz-dst-normalize",
)


def _load_module():
    spec = importlib.util.spec_from_file_location("humble_v5_analysis", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


analysis = _load_module()


def _rows(bank: str) -> list[dict]:
    path = LEDGER_DIR / f"{bank}.jsonl"
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _arm_task_costs(bank: str) -> dict[tuple[str, str], list[float]]:
    return analysis.run_costs(_rows(bank))


def _write_ledger(rows: list[dict]) -> Path:
    tmp = Path(tempfile.mkdtemp()) / "synthetic.jsonl"
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return tmp


def _synthetic(costs: dict[tuple[str, str], list[float]]) -> Path:
    """A minimal well-formed ledger: one trial row per arm to teach the config_hash join."""
    rows: list[dict] = []
    seen: set[str] = set()
    for (arm, task), vals in costs.items():
        chash = f"hash-{arm}"
        for i, cost in enumerate(vals):
            if chash not in seen:
                seen.add(chash)
                rows.append(
                    {
                        "kind": "trial",
                        "scenario": arm,
                        "config_hash": chash,
                        "task_id": task,
                        "repeat": i,
                        "status": "completed",
                        "verifier_results": {"c": True},
                    }
                )
            rows.append(
                {"kind": "run", "config_hash": chash, "task_id": task, "cost_usd_est": cost}
            )
    return _write_ledger(rows)


class SpendRailTests(unittest.TestCase):
    """The rail must count right and must actually stop."""

    def test_sums_run_rows_and_stays_green_below_the_rail(self) -> None:
        led = _synthetic({("bare", "t1"): [1.0, 2.0], ("armed", "t1"): [3.0]})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = analysis.main(["spend", str(led), "--stop-usd", "10"])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("$6.00", out)
        self.assertIn("headroom", out)

    def test_exits_non_zero_at_the_rail_so_a_shell_chain_breaks(self) -> None:
        led = _synthetic({("bare", "t1"): [80.0], ("armed", "t1"): [70.0]})
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            rc = analysis.main(["spend", str(led), "--stop-usd", "150"])
        self.assertEqual(rc, 2, "reaching the rail must be a non-zero exit, not a printed note")
        self.assertIn("STOP", err.getvalue())

    def test_default_rail_is_the_written_stop_rule(self) -> None:
        self.assertEqual(analysis.DEFAULT_STOP_USD, 150.0)

    def test_run_rows_are_attributed_through_config_hash(self) -> None:
        """Run rows carry no scenario (blindness); a broken join would silently mis-bill."""
        led = _synthetic({("bare", "t1"): [1.0], ("armed", "t1"): [4.0]})
        costs = analysis.run_costs(
            [json.loads(x) for x in led.read_text(encoding="utf-8").splitlines()]
        )
        self.assertEqual(costs[("bare", "t1")], [1.0])
        self.assertEqual(costs[("armed", "t1")], [4.0])
        self.assertNotIn("<unattributed>", {a for a, _ in costs})

    def test_empty_ledger_is_not_a_crash(self) -> None:
        led = _write_ledger([])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analysis.main(["spend", str(led)]), 0)
            self.assertEqual(analysis.main(["criteria", str(led)]), 0)
            self.assertEqual(analysis.main(["cost", str(led)]), 0)


class PairedTestTests(unittest.TestCase):
    def test_reproduces_a_known_paired_t(self) -> None:
        mean, sd, t_stat, df, p = analysis.paired_t([13.08, 21.20, 14.35, 15.60])
        self.assertAlmostEqual(mean, 16.06, places=1)
        self.assertEqual(df, 3)
        self.assertGreater(t_stat, 8.0)
        self.assertLess(p, 0.01)

    def test_p_value_matches_a_textbook_value(self) -> None:
        # t = 2.776 at df = 4 is the two-sided 5% critical value.
        self.assertAlmostEqual(analysis.t_test_two_sided_p(2.776, 4), 0.05, places=3)

    def test_no_difference_does_not_separate(self) -> None:
        _, _, _, _, p = analysis.paired_t([0.0, 0.0, 0.0, 0.0])
        self.assertEqual(p, 1.0)

    def test_single_pair_is_not_testable(self) -> None:
        self.assertEqual(analysis.paired_t([5.0])[4], 1.0)


class PublishedForecastTests(unittest.TestCase):
    """V5_NOTES' cost table must stay recomputable from v1/v2 — it gates real spend."""

    def setUp(self) -> None:
        self.v1, self.v2 = (
            _arm_task_costs("humble-vs-super-v1"),
            _arm_task_costs("humble-vs-super-v2"),
        )
        if not self.v1 or not self.v2:
            self.skipTest("v1/v2 ledgers absent — the forecast cannot be recomputed")

    def _arm_mean(self, costs, arm):
        vals = [c for t in V5_TASKS for c in costs.get((arm, t), [])]
        self.assertEqual(len(vals), 20, f"{arm}: expected 20 trials over v5's four tasks")
        return statistics.fmean(vals)

    def test_per_arm_rates_match_the_published_table(self) -> None:
        self.assertAlmostEqual(self._arm_mean(self.v1, "bare"), 0.2992, places=3)
        self.assertAlmostEqual(self._arm_mean(self.v2, "stack-humble"), 0.4966, places=3)
        self.assertAlmostEqual(self._arm_mean(self.v2, "stack-super"), 0.5771, places=3)

    def test_full_matrix_point_estimate_is_about_154_and_above_the_rail(self) -> None:
        total = (
            TRIALS_PER_ARM_AT_N20
            * OPUS5_FACTOR
            * (
                self._arm_mean(self.v1, "bare")
                + self._arm_mean(self.v2, "stack-humble")
                + self._arm_mean(self.v2, "stack-super")
            )
        )
        self.assertAlmostEqual(total, 153.76, places=1)
        self.assertGreater(
            total,
            analysis.DEFAULT_STOP_USD,
            "the n=20 matrix is forecast ABOVE the rail; V5_NOTES must keep saying so "
            "and Stage B must keep requiring an explicit rail decision",
        )

    def test_stage_a_fits_under_the_rail(self) -> None:
        stage_a = (
            TRIALS_PER_ARM_AT_N20
            / 4
            * OPUS5_FACTOR
            * (
                self._arm_mean(self.v1, "bare")
                + self._arm_mean(self.v2, "stack-humble")
                + self._arm_mean(self.v2, "stack-super")
            )
        )
        self.assertAlmostEqual(stage_a, 38.44, places=1)
        self.assertLess(stage_a, analysis.DEFAULT_STOP_USD)

    def test_per_spawn_cap_clears_the_observed_maximum_trial(self) -> None:
        """$1.75 was chosen to sit ABOVE the worst observed trial; $1.00 would truncate."""
        observed_max = max(
            c for costs in (self.v1, self.v2) for vals in costs.values() for c in vals
        )
        scaled = observed_max * OPUS5_FACTOR
        self.assertGreater(scaled, 1.0, "a $1.00 per-spawn cap would have truncated real trials")
        self.assertLess(
            scaled, 1.75, "the documented $1.75 per-spawn cap no longer clears the tail"
        )


class PublishedCeilingTests(unittest.TestCase):
    """The ceiling claims decide that the quality axis is not worth buying."""

    def setUp(self) -> None:
        rows = _rows("humble-vs-super-v1") + _rows("humble-vs-super-v2")
        if not rows:
            self.skipTest("v1/v2 ledgers absent")
        self.counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        self.armed: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        for r in rows:
            if r.get("kind") != "trial" or r.get("status") != "completed":
                continue
            for crit, val in (r.get("verifier_results") or {}).items():
                for bucket, skip_bare in ((self.counts, False), (self.armed, True)):
                    if skip_bare and r.get("scenario") == "bare":
                        continue
                    bucket[(r["task_id"], crit)][1] += 1
                    if val:
                        bucket[(r["task_id"], crit)][0] += 1

    def test_both_feature_tasks_are_fully_saturated_including_tests_present(self) -> None:
        for task in ("feature-csv-coalesce", "feature-retry-backoff"):
            slots = {c: v for (t, c), v in self.counts.items() if t == task}
            self.assertEqual(len(slots), 5, f"{task}: expected 5 criteria")
            self.assertIn("tests_present", slots)
            for crit, (passed, total) in slots.items():
                self.assertEqual(total, 40, f"{task}/{crit}: expected 40 pooled trials")
                self.assertEqual(
                    passed,
                    total,
                    f"{task}/{crit} is no longer saturated — V5_NOTES says the feature "
                    "half carries no quality signal; recheck that claim",
                )

    def test_correctness_criteria_ceiling_on_both_fix_tasks(self) -> None:
        for task in ("fix-offbyone-paginator", "fix-tz-dst-normalize"):
            for crit in ("fix_correct", "no_regression"):
                passed, total = self.counts[(task, crit)]
                self.assertEqual((passed, total), (50, 50), f"{task}/{crit} came off the ceiling")

    def test_paginator_is_the_only_slot_with_material_headroom(self) -> None:
        """Exactly one criterion-slot sits off the ceiling among the ARMED arms.

        "Off the ceiling" is <90%, not "<100%": `fix-tz-dst-normalize` is 44/45 (97.8%),
        a single stray failure, which is a ceiling with noise rather than a signal worth
        buying n for. The paginator at 71% is the whole quality axis, and V5_NOTES says so.
        """
        off_ceiling = sorted(k for k, (p, t) in self.armed.items() if t and p / t < 0.90)
        self.assertEqual(
            off_ceiling,
            [("fix-offbyone-paginator", "regression_test_present")],
            "V5_NOTES rests the whole quality axis on exactly one criterion of one task",
        )
        self.assertEqual(
            self.armed[("fix-offbyone-paginator", "regression_test_present")], [32, 45]
        )

        tz_pass, tz_total = self.armed[("fix-tz-dst-normalize", "regression_test_present")]
        self.assertEqual((tz_pass, tz_total), (44, 45))
        self.assertGreaterEqual(tz_pass / tz_total, 0.95, "the fix-tz slot is quoted as ceilinged")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
