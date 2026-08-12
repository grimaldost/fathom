"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from allocate.split import split_amount


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(split_amount(90, 3), [30, 30, 30])

        self.assertEqual(split_amount(8, 4), [2, 2, 2, 2])


if __name__ == "__main__":
    unittest.main()
