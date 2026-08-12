"""Regression checks added with the fix."""

import unittest

from rollup.hist import histogram


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(histogram([6], [0, 3, 6]), [0, 1])

        self.assertEqual(histogram([10], [0, 5, 10]), [0, 1])

    def test_related_cases(self):
        self.assertEqual(histogram([5], [0, 5]), [1])

        self.assertEqual(histogram([5, 6], [0, 5]), [1])


if __name__ == "__main__":
    unittest.main()
