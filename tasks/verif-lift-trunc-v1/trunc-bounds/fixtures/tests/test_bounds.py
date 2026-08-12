"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from ranges.bounds import lower_bound, upper_bound


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(lower_bound([1, 3, 5], 2), 1)

        self.assertEqual(lower_bound([], 4), -1)

    def test_shipped_cases_twin(self):
        self.assertEqual(upper_bound([1, 3, 5], 4), 1)

        self.assertEqual(upper_bound([], 4), -1)


if __name__ == "__main__":
    unittest.main()
