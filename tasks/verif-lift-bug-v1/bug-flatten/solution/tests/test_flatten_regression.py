"""Regression checks added with the fix."""

import unittest

from treekit.flatten import flatten


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(flatten([1, [], 2]), [1, 2])

        self.assertEqual(flatten([1, [2, 3], 4]), [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
