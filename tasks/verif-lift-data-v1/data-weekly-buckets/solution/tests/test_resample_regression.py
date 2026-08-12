"""Regression checks added with the fix."""

import unittest

from series2.resample import to_weekly


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(to_weekly([{'week': 'w1', 'amount': 2}], ['w1', 'w2']), [{'week': 'w1', 'amount': 2}, {'week': 'w2', 'amount': 0}])

    def test_related_cases(self):
        self.assertEqual(to_weekly([], ['w1', 'w2']), [{'week': 'w1', 'amount': 0}, {'week': 'w2', 'amount': 0}])

        self.assertEqual(to_weekly([{'week': 'w3', 'amount': 5}], ['w1', 'w2', 'w3']), [{'week': 'w1', 'amount': 0}, {'week': 'w2', 'amount': 0}, {'week': 'w3', 'amount': 5}])


if __name__ == "__main__":
    unittest.main()
