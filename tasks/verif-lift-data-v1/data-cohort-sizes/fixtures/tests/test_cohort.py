"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.cohort import cohort_sizes


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(cohort_sizes([{'id': 1, 'cohort': 'c1'}], [{'user_id': 1}]), {'c1': 1})


if __name__ == "__main__":
    unittest.main()
