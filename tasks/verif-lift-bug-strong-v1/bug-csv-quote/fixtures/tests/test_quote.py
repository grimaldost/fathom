"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from csvlite.quote import quote_field


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(quote_field('plain'), 'plain')

        self.assertEqual(quote_field('a,b'), '"a,b"')


if __name__ == "__main__":
    unittest.main()
