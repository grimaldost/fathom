"""Regression checks added with the fix."""

import unittest

from statkit.center import median


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(median([1, 2, 3, 4], strict=True), 2.5)
        self.assertEqual(median([10, 20], strict=True), 15.0)


if __name__ == "__main__":
    unittest.main()
