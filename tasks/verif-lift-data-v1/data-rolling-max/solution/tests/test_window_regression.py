"""Regression checks added with the fix."""

import unittest

from series2.window import rolling_max


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(rolling_max([1, 5, 3, 9], 2), [5, 5, 9])

        self.assertEqual(rolling_max([2, 2, 2], 3), [2])

    def test_related_cases(self):
        self.assertEqual(rolling_max([4], 1), [4])

        self.assertEqual(rolling_max([7, 7], 2), [7])


if __name__ == "__main__":
    unittest.main()
