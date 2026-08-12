"""Regression checks added with the fix."""

import unittest

from rollup.running import running_total


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(running_total([5, -2], strict=True), [5.0, 3.0])
        self.assertEqual(running_total([-1, -1], strict=True), [-1.0, -2.0])


if __name__ == "__main__":
    unittest.main()
