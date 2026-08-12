"""Regression checks added with the fix."""

import unittest

from reshape.pivot import pivot_counts


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(pivot_counts([{'r': 'a', 'c': 'x'}], 'r', 'c', ['x', 'y']), [{'r': 'a', 'x': 1, 'y': 0}])

    def test_related_cases(self):
        self.assertEqual(pivot_counts([{'r': 'a', 'c': 'x'}, {'r': 'a', 'c': 'x'}], 'r', 'c', ['x']), [{'r': 'a', 'x': 2}])


if __name__ == "__main__":
    unittest.main()
