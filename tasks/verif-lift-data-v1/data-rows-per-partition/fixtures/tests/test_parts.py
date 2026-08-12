"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.parts import rows_per_partition


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(rows_per_partition([{'partition': 'p1'}], ['p1', 'p2']), {'p1': 1, 'p2': 0})


if __name__ == "__main__":
    unittest.main()
