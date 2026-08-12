"""Regression checks added with the fix."""

import unittest

from rollup.share import pct_share


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(pct_share([{'name': 'a', 'value': 1}, {'name': 'b', 'value': 3}]), {'a': 25.0, 'b': 75.0})


if __name__ == "__main__":
    unittest.main()
