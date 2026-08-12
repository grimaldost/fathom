"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from series2.fill import forward_fill


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(forward_fill([1, None, 2]), [1, 1, 2])

        self.assertEqual(forward_fill([4, 5]), [4, 5])


if __name__ == "__main__":
    unittest.main()
