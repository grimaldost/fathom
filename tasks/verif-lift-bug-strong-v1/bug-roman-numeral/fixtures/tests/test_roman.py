"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from numerals.roman import to_roman


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(to_roman(3), 'III')

        self.assertEqual(to_roman(2026), 'MMXXVI')

        self.assertEqual(to_roman(15), 'XV')


if __name__ == "__main__":
    unittest.main()
