"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from treekit.flatten import flatten


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(flatten([1, 2, 3]), [1, 2, 3])

        self.assertEqual(flatten([1, [2]]), [1, 2])


if __name__ == "__main__":
    unittest.main()
