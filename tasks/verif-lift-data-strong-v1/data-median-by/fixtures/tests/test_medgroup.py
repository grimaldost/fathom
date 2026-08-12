"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.medgroup import median_by


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(median_by([{'g': 'a', 'value': 1}, {'g': 'a', 'value': 3}], 'g'), {'a': 2.0})


if __name__ == "__main__":
    unittest.main()
