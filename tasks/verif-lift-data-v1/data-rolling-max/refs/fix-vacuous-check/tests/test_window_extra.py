"""Regression checks added with the fix."""

import unittest

from series2.window import rolling_max


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(rolling_max([], 2), [])

        self.assertEqual(rolling_max([1, 2], 5), [])


if __name__ == "__main__":
    unittest.main()
