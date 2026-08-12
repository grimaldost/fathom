"""Regression checks added with the fix."""

import unittest

from moneykit.totals import sum_amounts


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        with self.assertRaises(ValueError):
            sum_amounts([{'currency': 'AAA', 'minor': 100}, {'currency': 'BBB', 'minor': 250}])

    def test_related_cases(self):
        with self.assertRaises(ValueError):
            sum_amounts([])


if __name__ == "__main__":
    unittest.main()
