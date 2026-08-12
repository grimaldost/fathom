"""Regression checks added with the fix."""

import unittest

from searchkit.bisect import first_index


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(first_index([1, 2, 2, 2, 3], 2), 1)

        self.assertEqual(first_index([5, 5, 5], 5), 0)


if __name__ == "__main__":
    unittest.main()
