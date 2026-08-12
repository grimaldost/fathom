"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.share import pct_share


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(pct_share([{'name': 'a', 'value': 1}, {'name': 'b', 'value': 3}]), {'a': 25.0, 'b': 75.0})


if __name__ == "__main__":
    unittest.main()
