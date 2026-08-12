"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from units.abbrev import abbrev_count, abbrev_bytes


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(abbrev_count(1500), '1.5k')

        self.assertEqual(abbrev_count(42), '42')

    def test_shipped_cases_twin(self):
        self.assertEqual(abbrev_bytes(1536), '1.5KiB')

        self.assertEqual(abbrev_bytes(42), '42B')


if __name__ == "__main__":
    unittest.main()
