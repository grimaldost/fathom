"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from statkit.center import median


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(median([3, 1, 2]), 2.0)

        self.assertEqual(median([5]), 5.0)


if __name__ == "__main__":
    unittest.main()
