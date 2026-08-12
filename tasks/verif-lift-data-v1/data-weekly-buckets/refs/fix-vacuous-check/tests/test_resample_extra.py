"""Regression checks added with the fix."""

import unittest

from series2.resample import to_weekly


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(to_weekly([{'week': 'w1', 'amount': 2}, {'week': 'w2', 'amount': 3}], ['w1', 'w2']), [{'week': 'w1', 'amount': 2}, {'week': 'w2', 'amount': 3}])


if __name__ == "__main__":
    unittest.main()
