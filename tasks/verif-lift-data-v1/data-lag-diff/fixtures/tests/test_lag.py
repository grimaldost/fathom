"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from series2.lag import lag_diff


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(lag_diff([{'t': 1, 'value': 10}, {'t': 2, 'value': 13}]), [{'t': 1, 'diff': None}, {'t': 2, 'diff': 3}])


if __name__ == "__main__":
    unittest.main()
