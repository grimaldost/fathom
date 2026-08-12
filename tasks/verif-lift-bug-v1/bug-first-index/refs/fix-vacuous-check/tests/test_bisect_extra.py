"""Regression checks added with the fix."""

import unittest

from searchkit.bisect import first_index


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(first_index([1, 2, 3, 4], 3), 2)

        self.assertEqual(first_index([1, 2, 3], 9), -1)


if __name__ == "__main__":
    unittest.main()
