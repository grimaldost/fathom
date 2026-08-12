"""Regression checks added with the fix."""

import unittest

from allocate.split import split_amount


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(split_amount(100, 3), [34, 33, 33])

        self.assertEqual(split_amount(7, 2), [4, 3])


if __name__ == "__main__":
    unittest.main()
