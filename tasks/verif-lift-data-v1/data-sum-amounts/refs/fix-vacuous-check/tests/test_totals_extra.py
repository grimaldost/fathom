"""Regression checks added with the fix."""

import unittest

from moneykit.totals import sum_amounts


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(sum_amounts([{'currency': 'AAA', 'minor': 100}, {'currency': 'AAA', 'minor': 250}]), {'currency': 'AAA', 'minor': 350})


if __name__ == "__main__":
    unittest.main()
