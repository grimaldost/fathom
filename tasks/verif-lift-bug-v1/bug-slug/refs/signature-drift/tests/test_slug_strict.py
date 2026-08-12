"""Regression checks added with the fix."""

import unittest

from textkit.slug import slugify


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(slugify('a -- b', strict=True), 'a-b')
        self.assertEqual(slugify('Report: Q3, final', strict=True), 'report-q3-final')


if __name__ == "__main__":
    unittest.main()
