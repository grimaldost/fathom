"""Regression checks added with the fix."""

import unittest

from numerals.roman import to_roman


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(to_roman(4, strict=True), 'IV')
        self.assertEqual(to_roman(9, strict=True), 'IX')
        self.assertEqual(to_roman(1944, strict=True), 'MCMXLIV')


if __name__ == "__main__":
    unittest.main()
