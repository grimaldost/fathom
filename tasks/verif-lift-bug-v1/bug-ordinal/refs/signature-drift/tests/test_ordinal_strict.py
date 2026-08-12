"""Regression checks added with the fix."""

import unittest

from textkit.ordinal import ordinal


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(ordinal(11, strict=True), '11th')
        self.assertEqual(ordinal(12, strict=True), '12th')
        self.assertEqual(ordinal(113, strict=True), '113th')


if __name__ == "__main__":
    unittest.main()
