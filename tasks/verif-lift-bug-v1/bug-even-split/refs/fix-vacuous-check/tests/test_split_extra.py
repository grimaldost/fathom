"""Regression checks added with the fix."""

import unittest

from allocate.split import split_amount


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(split_amount(90, 3), [30, 30, 30])

        self.assertEqual(split_amount(8, 4), [2, 2, 2, 2])


if __name__ == "__main__":
    unittest.main()
