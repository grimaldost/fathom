"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from paging.window import page_bounds


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(page_bounds(20, 5), [[0, 5], [5, 10], [10, 15], [15, 20]])

        self.assertEqual(page_bounds(6, 3), [[0, 3], [3, 6]])


if __name__ == "__main__":
    unittest.main()
