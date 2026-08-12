"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.wavg import weighted_avg


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(weighted_avg([{'value': 10, 'weight': 1}, {'value': 20, 'weight': 3}]), 17.5)

        self.assertEqual(weighted_avg([]), None)


if __name__ == "__main__":
    unittest.main()
