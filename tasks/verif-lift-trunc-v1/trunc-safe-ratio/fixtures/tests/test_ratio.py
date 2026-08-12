"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from ratios.ratio import safe_ratio, safe_growth


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(safe_ratio(1.0, 4.0), 0.25)

        self.assertEqual(safe_ratio(3.0, 6.0), 0.5)

    def test_shipped_cases_twin(self):
        self.assertEqual(safe_growth(4.0, 5.0), 0.25)


if __name__ == "__main__":
    unittest.main()
