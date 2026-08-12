"""Regression checks added with the fix."""

import unittest

from series2.lag import lag_diff


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(lag_diff([{'t': 1, 'value': 10}, {'t': 2, 'value': 13}]), [{'t': 1, 'diff': None}, {'t': 2, 'diff': 3}])


if __name__ == "__main__":
    unittest.main()
