"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from phrasing.plural import plural_items, plural_errors


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(plural_items(1), '1 item')

        self.assertEqual(plural_items(3), '3 items')

    def test_shipped_cases_twin(self):
        self.assertEqual(plural_errors(1), '1 error')

        self.assertEqual(plural_errors(4), '4 errors')


if __name__ == "__main__":
    unittest.main()
