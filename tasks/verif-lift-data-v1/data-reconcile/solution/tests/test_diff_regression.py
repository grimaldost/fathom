"""Regression checks added with the fix."""

import unittest

from recon.diff import reconcile


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(reconcile({'a': 5}, {'a': 8}), {'a': 3})

        self.assertEqual(reconcile({'a': 10}, {'a': 4}), {'a': -6})

    def test_related_cases(self):
        self.assertEqual(reconcile({}, {'b': 2}), {'b': 2})

        self.assertEqual(reconcile({'a': 1}, {'b': 2}), {'a': -1, 'b': 2})


if __name__ == "__main__":
    unittest.main()
