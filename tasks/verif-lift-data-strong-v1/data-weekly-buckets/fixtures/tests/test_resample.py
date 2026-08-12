"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from series2.resample import to_weekly


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(to_weekly([{'week': 'w1', 'amount': 2}, {'week': 'w2', 'amount': 3}], ['w1', 'w2']), [{'week': 'w1', 'amount': 2}, {'week': 'w2', 'amount': 3}])


if __name__ == "__main__":
    unittest.main()
