"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from searchkit.bisect import first_index


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(first_index([1, 2, 3, 4], 3), 2)

        self.assertEqual(first_index([1, 2, 3], 9), -1)


if __name__ == "__main__":
    unittest.main()
