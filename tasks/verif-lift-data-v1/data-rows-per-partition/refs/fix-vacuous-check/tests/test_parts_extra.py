"""Regression checks added with the fix."""

import unittest

from rollup.parts import rows_per_partition


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(rows_per_partition([{'partition': 'p1'}], ['p1', 'p2']), {'p1': 1, 'p2': 0})


if __name__ == "__main__":
    unittest.main()
