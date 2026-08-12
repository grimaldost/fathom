"""Regression checks added with the fix."""

import unittest

from rollup.share import pct_share


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(pct_share([{'name': 'a', 'value': 5}, {'name': 'b', 'value': -5}], strict=True), {'a': 0.0, 'b': 0.0})
        self.assertEqual(pct_share([{'name': 'a', 'value': 2}, {'name': 'b', 'value': -2}], strict=True), {'a': 0.0, 'b': 0.0})


if __name__ == "__main__":
    unittest.main()
