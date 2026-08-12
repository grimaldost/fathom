"""Regression checks added with the fix."""

import unittest

from rollup.running import running_total


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(running_total([5, -2]), [5.0, 3.0])

        self.assertEqual(running_total([-1, -1]), [-1.0, -2.0])

    def test_related_cases(self):
        self.assertEqual(running_total([3, -3, 4]), [3.0, 0.0, 4.0])

        self.assertEqual(running_total([0, -5, 5]), [0.0, -5.0, 0.0])


if __name__ == "__main__":
    unittest.main()
