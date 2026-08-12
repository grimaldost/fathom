"""Regression checks added with the fix."""

import unittest

from statkit.center import median


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(median([1, 2, 3, 4]), 2.5)

        self.assertEqual(median([10, 20]), 15.0)


if __name__ == "__main__":
    unittest.main()
