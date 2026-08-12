"""Regression checks added with the fix."""

import unittest

from rollup.medgroup import median_by


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(median_by([{'g': 'a', 'value': 1}, {'g': 'a', 'value': 2}, {'g': 'a', 'value': 9}], 'g', strict=True), {'a': 2.0})


if __name__ == "__main__":
    unittest.main()
