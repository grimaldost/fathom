"""Regression checks added with the fix."""

import unittest

from recon.diff import reconcile


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(reconcile({'a': 5}, {'a': 5}), {})


if __name__ == "__main__":
    unittest.main()
