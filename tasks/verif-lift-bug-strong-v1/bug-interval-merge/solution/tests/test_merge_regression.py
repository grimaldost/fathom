"""Regression checks added with the fix."""

import unittest

from intervals.merge import merge_spans


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(merge_spans([[0, 5], [5, 9]]), [[0, 9]])

        self.assertEqual(merge_spans([[1, 3], [3, 4], [4, 6]]), [[1, 6]])


if __name__ == "__main__":
    unittest.main()
