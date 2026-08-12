"""Regression checks added with the fix."""

import unittest

from paging.window import page_bounds


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(page_bounds(22, 5, strict=True), [[0, 5], [5, 10], [10, 15], [15, 20], [20, 22]])
        self.assertEqual(page_bounds(4, 10, strict=True), [[0, 4]])


if __name__ == "__main__":
    unittest.main()
