"""Regression checks added with the fix."""

import unittest

from treekit.flatten import flatten


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(flatten([1, [], 2], strict=True), [1, 2])
        self.assertEqual(flatten([1, [2, 3], 4], strict=True), [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
