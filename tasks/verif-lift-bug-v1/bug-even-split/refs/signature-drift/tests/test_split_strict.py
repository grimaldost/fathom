"""Regression checks added with the fix."""

import unittest

from allocate.split import split_amount


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(split_amount(100, 3, strict=True), [34, 33, 33])
        self.assertEqual(split_amount(7, 2, strict=True), [4, 3])


if __name__ == "__main__":
    unittest.main()
