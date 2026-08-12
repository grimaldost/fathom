"""Regression checks added with the fix."""

import unittest

from rollup.wavg import weighted_avg


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(weighted_avg([{'value': 10, 'weight': 0}]), None)

        self.assertEqual(weighted_avg([{'value': 5, 'weight': 0}, {'value': 7, 'weight': 0}]), None)

    def test_related_cases(self):
        self.assertEqual(weighted_avg([{'value': 4, 'weight': 2}, {'value': 6, 'weight': -2}]), None)


if __name__ == "__main__":
    unittest.main()
