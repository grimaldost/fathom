"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from reshape.pivot import pivot_counts


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(pivot_counts([{'r': 'a', 'c': 'x'}], 'r', 'c', ['x']), [{'r': 'a', 'x': 1}])


if __name__ == "__main__":
    unittest.main()
