"""Regression checks added with the fix."""

import unittest

from rollup.share import pct_share


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(pct_share([{'name': 'a', 'value': 5}, {'name': 'b', 'value': -5}]), {'a': 0.0, 'b': 0.0})

        self.assertEqual(pct_share([{'name': 'a', 'value': 2}, {'name': 'b', 'value': -2}]), {'a': 0.0, 'b': 0.0})

    def test_related_cases(self):
        self.assertEqual(pct_share([{'name': 'a', 'value': None}, {'name': 'b', 'value': 3}]), {'a': 0.0, 'b': 100.0})

        self.assertEqual(pct_share([{'name': 'a', 'value': None}]), {'a': 0.0})


if __name__ == "__main__":
    unittest.main()
