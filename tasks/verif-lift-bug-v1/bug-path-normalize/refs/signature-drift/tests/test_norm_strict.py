"""Regression checks added with the fix."""

import unittest

from pathkit.norm import normalize


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(normalize('a/b/..', strict=True), 'a')
        self.assertEqual(normalize('a/b/c/../..', strict=True), 'a')


if __name__ == "__main__":
    unittest.main()
