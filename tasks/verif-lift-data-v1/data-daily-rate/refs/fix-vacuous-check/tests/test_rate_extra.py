"""Regression checks added with the fix."""

import unittest

from rollup.rate import daily_rate


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(daily_rate([{'day': 'd1', 'events': 10, 'actors': 4}]), {'d1': 2.5})


if __name__ == "__main__":
    unittest.main()
