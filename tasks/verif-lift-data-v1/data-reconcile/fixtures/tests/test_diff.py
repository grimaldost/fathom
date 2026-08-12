"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from recon.diff import reconcile


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(reconcile({'a': 5}, {'a': 5}), {})


if __name__ == "__main__":
    unittest.main()
