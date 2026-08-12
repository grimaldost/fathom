"""Regression checks added with the fix."""

import unittest

from paging.window import page_bounds


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(page_bounds(20, 5), [[0, 5], [5, 10], [10, 15], [15, 20]])

        self.assertEqual(page_bounds(6, 3), [[0, 3], [3, 6]])


if __name__ == "__main__":
    unittest.main()
