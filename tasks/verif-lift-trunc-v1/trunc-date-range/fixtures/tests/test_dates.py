"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from calendars.dates import fmt_day, fmt_range


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(fmt_day(2026, 11, 30), '2026-11-30')

    def test_shipped_cases_twin(self):
        self.assertEqual(fmt_range([2026, 11, 30], [2026, 12, 31]), '2026-11-30 to 2026-12-31')


if __name__ == "__main__":
    unittest.main()
