"""Regression checks added with the fix."""

import unittest

from rollup.wavg import weighted_avg


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(weighted_avg([{'value': 10, 'weight': 1}, {'value': 20, 'weight': 3}]), 17.5)

        self.assertEqual(weighted_avg([]), None)


if __name__ == "__main__":
    unittest.main()
