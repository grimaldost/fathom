"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from pathkit.norm import normalize


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(normalize('a/./b/c'), 'a/b/c')

        self.assertEqual(normalize('a/../b/c'), 'b/c')


if __name__ == "__main__":
    unittest.main()
