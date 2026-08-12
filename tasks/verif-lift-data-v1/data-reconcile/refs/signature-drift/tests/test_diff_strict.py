"""Regression checks added with the fix."""

import unittest

from recon.diff import reconcile


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(reconcile({'a': 5}, {'a': 8}, strict=True), {'a': 3})
        self.assertEqual(reconcile({'a': 10}, {'a': 4}, strict=True), {'a': -6})


if __name__ == "__main__":
    unittest.main()
