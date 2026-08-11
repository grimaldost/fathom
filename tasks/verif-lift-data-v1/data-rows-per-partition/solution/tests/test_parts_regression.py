"""Regression checks added with the fix."""

import unittest

from rollup.parts import rows_per_partition


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(rows_per_partition([{'partition': None}], ['p1']), {'p1': 0, '__unpartitioned__': 1})

    def test_related_cases(self):
        self.assertEqual(rows_per_partition([{'partition': None}, {'partition': 'p1'}, {'partition': None}], ['p1']), {'p1': 1, '__unpartitioned__': 2})


if __name__ == "__main__":
    unittest.main()
