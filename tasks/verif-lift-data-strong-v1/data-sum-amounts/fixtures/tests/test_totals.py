"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from moneykit.totals import sum_amounts


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(sum_amounts([{'currency': 'AAA', 'minor': 100}, {'currency': 'AAA', 'minor': 250}]), {'currency': 'AAA', 'minor': 350})


if __name__ == "__main__":
    unittest.main()
