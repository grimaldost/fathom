"""Tests for tools/readout_multiagent.py — the helpers the iteration-2 family adds.

Known values: Fisher's tea-tasting table, Newcombe's 1998 worked example (56/70 vs 48/80,
method 10: 0.0524 to 0.3339), and small Mann-Whitney cases whose exact two-sided p is a
count over C(m+n, m) arrangements.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import readout_multiagent as ro  # noqa: E402


class SplitScenarioTests(unittest.TestCase):
    def test_iter1_default_family(self):
        self.assertEqual(ro.split_scenario("perpr-haiku"), ("perpr", "haiku"))
        self.assertEqual(ro.split_scenario("final-sonnet"), ("final", "sonnet"))
        self.assertIsNone(ro.split_scenario("placebo2-haiku"))
        self.assertIsNone(ro.split_scenario("control-opus"))
        self.assertIsNone(ro.split_scenario("control"))

    def test_iter2_family_splits_on_the_last_dash(self):
        arms = ro.FAMILIES["iter2"]["arms"]
        self.assertEqual(ro.split_scenario("placebo2-haiku", arms), ("placebo2", "haiku"))
        self.assertEqual(ro.split_scenario("hook2-sonnet", arms), ("hook2", "sonnet"))
        self.assertIsNone(ro.split_scenario("perpr-haiku", arms))

    def test_iter2_contrasts_are_the_declared_four(self):
        self.assertEqual(
            ro.FAMILIES["iter2"]["contrasts"],
            (
                ("hook2", "control2"),
                ("hook2", "placebo2"),
                ("perpr2", "placebo2"),
                ("perpr2", "control2"),
            ),
        )


class FisherTests(unittest.TestCase):
    def test_tea_tasting_table(self):
        self.assertAlmostEqual(ro.fisher_greater(3, 4, 1, 4), 0.2429, places=4)
        self.assertAlmostEqual(ro.fisher_two_sided(3, 4, 1, 4), 0.4857, places=4)

    def test_two_sided_is_symmetric_and_bounded(self):
        self.assertAlmostEqual(
            ro.fisher_two_sided(14, 16, 4, 16), ro.fisher_two_sided(4, 16, 14, 16)
        )
        self.assertEqual(ro.fisher_two_sided(8, 16, 8, 16), 1.0)
        self.assertEqual(ro.fisher_two_sided(0, 0, 0, 0), 1.0)


class NewcombeTests(unittest.TestCase):
    def test_published_example(self):
        d, lo, hi = ro.newcombe(56, 70, 48, 80)
        self.assertAlmostEqual(d, 0.2, places=6)
        self.assertAlmostEqual(lo, 0.0524, places=4)
        self.assertAlmostEqual(hi, 0.3339, places=4)

    def test_sign_flips_with_the_order(self):
        d1, lo1, hi1 = ro.newcombe(14, 16, 4, 16)
        d2, lo2, hi2 = ro.newcombe(4, 16, 14, 16)
        self.assertAlmostEqual(d1, -d2)
        self.assertAlmostEqual(lo1, -hi2)
        self.assertAlmostEqual(hi1, -lo2)


class MannWhitneyTests(unittest.TestCase):
    def test_u_counts_small_tables(self):
        self.assertEqual(ro._u_counts(1, 1), [1, 1])
        self.assertEqual(ro._u_counts(2, 2), [1, 1, 2, 1, 1])
        self.assertEqual(ro._u_counts(3, 3), [1, 1, 2, 3, 3, 3, 3, 2, 1, 1])
        self.assertEqual(sum(ro._u_counts(16, 16)), 601080390)  # C(32, 16)

    def test_exact_known_values(self):
        u, p, method = ro.mann_whitney([1, 2, 3], [4, 5, 6])
        self.assertEqual((u, method), (0.0, "exact"))
        self.assertAlmostEqual(p, 2 / 20)
        u, p, method = ro.mann_whitney([1, 3, 5], [2, 4, 6])
        self.assertEqual(u, 3.0)
        self.assertAlmostEqual(p, 14 / 20)
        u, p, _ = ro.mann_whitney([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
        self.assertAlmostEqual(p, 2 / 252)

    def test_exact_is_symmetric_and_capped(self):
        x, y = [1.1, 2.2, 3.3, 9.9], [4.4, 5.5, 6.6, 0.5]
        _, p_xy, _ = ro.mann_whitney(x, y)
        _, p_yx, _ = ro.mann_whitney(y, x)
        self.assertAlmostEqual(p_xy, p_yx)
        self.assertLessEqual(p_xy, 1.0)

    def test_ties_fall_back_to_the_normal_approximation(self):
        u, p, method = ro.mann_whitney([36, 36, 37, 40], [36, 38, 41, 41])
        self.assertIn("normal", method)
        self.assertGreater(p, 0.0)
        self.assertLessEqual(p, 1.0)
        _, p_rev, _ = ro.mann_whitney([36, 38, 41, 41], [36, 36, 37, 40])
        self.assertAlmostEqual(p, p_rev)
        _, p_all, method_all = ro.mann_whitney([5, 5, 5], [5, 5])
        self.assertEqual(p_all, 1.0)
        self.assertIn("normal", method_all)

    def test_normal_approximation_tracks_a_clear_separation(self):
        # sixteen vs sixteen with one tie: far apart, so p must be tiny
        x = [10, 10] + list(range(11, 25))
        y = list(range(30, 46))
        _, p, method = ro.mann_whitney(x, y)
        self.assertIn("normal", method)
        self.assertLess(p, 1e-4)


class MedianIqrTests(unittest.TestCase):
    def test_inclusive_quartiles(self):
        self.assertEqual(ro.median_iqr([1, 2, 3, 4]), (2.5, 1.75, 3.25))
        self.assertEqual(ro.median_iqr([7.0]), (7.0, 7.0, 7.0))


class PerTrialTurnsTests(unittest.TestCase):
    def test_sums_run_rows_per_trial_key(self):
        runs = [
            {"config_hash": "h", "repeat": 0, "turns": 30},
            {"config_hash": "h", "repeat": 0, "turns": 5},
            {"config_hash": "h", "repeat": 1, "turns": 12},
            {"config_hash": "g", "repeat": 0},
        ]
        self.assertEqual(ro.per_trial_turns(runs), {("h", 0): 35, ("h", 1): 12})


if __name__ == "__main__":
    unittest.main()
