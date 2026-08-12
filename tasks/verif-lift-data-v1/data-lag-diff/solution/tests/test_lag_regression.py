"""Regression checks added with the fix."""

import unittest

from series2.lag import lag_diff


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(lag_diff([{'t': 2, 'value': 13}, {'t': 1, 'value': 10}]), [{'t': 1, 'diff': None}, {'t': 2, 'diff': 3}])

    def test_related_cases(self):
        self.assertEqual(lag_diff([{'t': 3, 'value': 6}, {'t': 1, 'value': 1}, {'t': 2, 'value': 4}]), [{'t': 1, 'diff': None}, {'t': 2, 'diff': 3}, {'t': 3, 'diff': 2}])


if __name__ == "__main__":
    unittest.main()
