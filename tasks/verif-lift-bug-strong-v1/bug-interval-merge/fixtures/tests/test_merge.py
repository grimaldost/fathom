"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from intervals.merge import merge_spans


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(merge_spans([[0, 4], [2, 7]]), [[0, 7]])

        self.assertEqual(merge_spans([[0, 2], [5, 8]]), [[0, 2], [5, 8]])


if __name__ == "__main__":
    unittest.main()
