"""Regression checks added with the fix."""

import unittest

from series2.window import rolling_max


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(rolling_max([1, 5, 3, 9], 2, strict=True), [5, 5, 9])
        self.assertEqual(rolling_max([2, 2, 2], 3, strict=True), [2])


if __name__ == "__main__":
    unittest.main()
