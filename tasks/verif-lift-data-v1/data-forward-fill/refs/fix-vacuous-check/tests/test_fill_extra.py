"""Regression checks added with the fix."""

import unittest

from series2.fill import forward_fill


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(forward_fill([1, None, 2]), [1, 1, 2])

        self.assertEqual(forward_fill([4, 5]), [4, 5])


if __name__ == "__main__":
    unittest.main()
