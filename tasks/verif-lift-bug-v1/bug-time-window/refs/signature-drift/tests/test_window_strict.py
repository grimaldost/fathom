"""Regression checks added with the fix."""

import unittest

from sched.window import slots


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(slots(0, 30, 10, strict=True), [0, 10, 20])
        self.assertEqual(slots(60, 120, 30, strict=True), [60, 90])


if __name__ == "__main__":
    unittest.main()
