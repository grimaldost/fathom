"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from scoring.clamp import clamp_score, clamp_weight


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(clamp_score(-5.0), 0.0)

        self.assertEqual(clamp_score(50.0), 50.0)

    def test_shipped_cases_twin(self):
        self.assertEqual(clamp_weight(-0.5), 0.0)

        self.assertEqual(clamp_weight(0.25), 0.25)


if __name__ == "__main__":
    unittest.main()
