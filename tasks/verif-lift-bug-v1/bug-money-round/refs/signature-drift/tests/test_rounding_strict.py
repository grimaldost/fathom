"""Regression checks added with the fix."""

import unittest

from moneykit.rounding import round_half_even


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(round_half_even(2.5, 0, strict=True), 2.0)
        self.assertEqual(round_half_even(3.5, 0, strict=True), 4.0)
        self.assertEqual(round_half_even(0.125, 2, strict=True), 0.12)


if __name__ == "__main__":
    unittest.main()
