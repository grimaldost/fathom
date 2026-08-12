"""Regression checks added with the fix."""

import unittest

from cleanse.keys import normalize_keys


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(normalize_keys([{'k': 'ABC'}], 'k', strict=True), [{'k': 'abc'}])
        self.assertEqual(normalize_keys([{'k': ' MiXeD '}], 'k', strict=True), [{'k': 'mixed'}])


if __name__ == "__main__":
    unittest.main()
