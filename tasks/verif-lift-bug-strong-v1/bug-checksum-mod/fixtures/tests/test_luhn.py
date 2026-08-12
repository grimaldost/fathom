"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from validate2.luhn import is_valid


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(is_valid('22'), False)

        self.assertEqual(is_valid('1111'), False)

        self.assertEqual(is_valid('79927398710'), False)


if __name__ == "__main__":
    unittest.main()
