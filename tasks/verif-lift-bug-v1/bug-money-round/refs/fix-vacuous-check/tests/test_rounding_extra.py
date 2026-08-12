"""Regression checks added with the fix."""

import unittest

from moneykit.rounding import round_half_even


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(round_half_even(2.4, 0), 2.0)

        self.assertEqual(round_half_even(2.6, 0), 3.0)


if __name__ == "__main__":
    unittest.main()
