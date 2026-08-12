"""Regression checks added with the fix."""

import unittest

from reshape.pivot import pivot_counts


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(pivot_counts([{'r': 'a', 'c': 'x'}], 'r', 'c', ['x', 'y'], strict=True), [{'r': 'a', 'x': 1, 'y': 0}])


if __name__ == "__main__":
    unittest.main()
