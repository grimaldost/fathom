"""Regression checks added with the fix."""

import unittest

from reshape.pivot import pivot_counts


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(pivot_counts([{'r': 'a', 'c': 'x'}], 'r', 'c', ['x']), [{'r': 'a', 'x': 1}])


if __name__ == "__main__":
    unittest.main()
