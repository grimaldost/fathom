"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from reportkit.summary import format_share, format_delta


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(format_share(0.12), '12.0%')

        self.assertEqual(format_share(0.5), '50.0%')

    def test_shipped_cases_twin(self):
        self.assertEqual(format_delta(0.12), '+12.0%')


if __name__ == "__main__":
    unittest.main()
