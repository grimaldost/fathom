"""Regression checks added with the fix."""

import unittest

from moneykit.totals import sum_amounts


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        with self.assertRaises(ValueError):
            sum_amounts([{'currency': 'AAA', 'minor': 100}, {'currency': 'BBB', 'minor': 250}], strict=True)


if __name__ == "__main__":
    unittest.main()
