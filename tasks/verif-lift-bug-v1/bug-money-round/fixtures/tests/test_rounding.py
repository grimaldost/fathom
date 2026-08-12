"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from moneykit.rounding import round_half_even


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(round_half_even(2.4, 0), 2.0)

        self.assertEqual(round_half_even(2.6, 0), 3.0)


if __name__ == "__main__":
    unittest.main()
