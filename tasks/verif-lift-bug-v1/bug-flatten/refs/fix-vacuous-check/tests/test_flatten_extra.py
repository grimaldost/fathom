"""Regression checks added with the fix."""

import unittest

from treekit.flatten import flatten


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(flatten([1, 2, 3]), [1, 2, 3])

        self.assertEqual(flatten([1, [2]]), [1, 2])


if __name__ == "__main__":
    unittest.main()
