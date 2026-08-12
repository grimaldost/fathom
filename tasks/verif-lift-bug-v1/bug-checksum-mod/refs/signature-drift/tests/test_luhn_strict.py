"""Regression checks added with the fix."""

import unittest

from validate2.luhn import is_valid


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(is_valid('18', strict=True), True)
        self.assertEqual(is_valid('1230', strict=True), True)
        self.assertEqual(is_valid('4539578763621486', strict=True), True)


if __name__ == "__main__":
    unittest.main()
