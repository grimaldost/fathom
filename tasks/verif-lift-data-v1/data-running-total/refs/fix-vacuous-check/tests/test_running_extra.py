"""Regression checks added with the fix."""

import unittest

from rollup.running import running_total


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(running_total([1, 2, 3]), [1.0, 3.0, 6.0])

        self.assertEqual(running_total([]), [])


if __name__ == "__main__":
    unittest.main()
