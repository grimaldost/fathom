"""Regression checks added with the fix."""

import unittest

from rollup.hist import histogram


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(histogram([1, 2, 5], [0, 3, 6]), [2, 1])

        self.assertEqual(histogram([], [0, 1]), [0])


if __name__ == "__main__":
    unittest.main()
