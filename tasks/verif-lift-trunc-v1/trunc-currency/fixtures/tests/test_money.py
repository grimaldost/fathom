"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from amounts.money import fmt_amount, fmt_total


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(fmt_amount(1234), '12.34')

        self.assertEqual(fmt_amount(5), '0.05')

    def test_shipped_cases_twin(self):
        self.assertEqual(fmt_total([1234]), '12.34')


if __name__ == "__main__":
    unittest.main()
