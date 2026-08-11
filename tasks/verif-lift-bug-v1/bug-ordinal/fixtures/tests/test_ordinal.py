"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from textkit.ordinal import ordinal


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(ordinal(1), '1st')

        self.assertEqual(ordinal(22), '22nd')

        self.assertEqual(ordinal(5), '5th')


if __name__ == "__main__":
    unittest.main()
