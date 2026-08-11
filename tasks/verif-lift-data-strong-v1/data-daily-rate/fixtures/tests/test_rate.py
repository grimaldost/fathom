"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.rate import daily_rate


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(daily_rate([{'day': 'd1', 'events': 10, 'actors': 4}]), {'d1': 2.5})


if __name__ == "__main__":
    unittest.main()
