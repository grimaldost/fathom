"""Regression checks added with the fix."""

import unittest

from rollup.wavg import weighted_avg


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(weighted_avg([{'value': 10, 'weight': 0}], strict=True), None)
        self.assertEqual(weighted_avg([{'value': 5, 'weight': 0}, {'value': 7, 'weight': 0}], strict=True), None)


if __name__ == "__main__":
    unittest.main()
