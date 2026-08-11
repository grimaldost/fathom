"""Regression checks added with the fix."""

import unittest

from intervals.merge import merge_spans


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(merge_spans([[0, 4], [2, 7]]), [[0, 7]])

        self.assertEqual(merge_spans([[0, 2], [5, 8]]), [[0, 2], [5, 8]])


if __name__ == "__main__":
    unittest.main()
