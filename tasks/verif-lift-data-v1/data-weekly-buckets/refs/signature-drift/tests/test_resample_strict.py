"""Regression checks added with the fix."""

import unittest

from series2.resample import to_weekly


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(to_weekly([{'week': 'w1', 'amount': 2}], ['w1', 'w2'], strict=True), [{'week': 'w1', 'amount': 2}, {'week': 'w2', 'amount': 0}])


if __name__ == "__main__":
    unittest.main()
