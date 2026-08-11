"""Regression checks added with the fix."""

import unittest

from statkit.center import median


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(median([3, 1, 2]), 2.0)

        self.assertEqual(median([5]), 5.0)


if __name__ == "__main__":
    unittest.main()
