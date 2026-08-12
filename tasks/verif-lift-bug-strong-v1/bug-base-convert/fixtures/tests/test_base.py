"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from numerals.base import to_base


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(to_base(10, 2), '1010')

        self.assertEqual(to_base(255, 16), 'ff')

        self.assertEqual(to_base(7, 8), '7')


if __name__ == "__main__":
    unittest.main()
