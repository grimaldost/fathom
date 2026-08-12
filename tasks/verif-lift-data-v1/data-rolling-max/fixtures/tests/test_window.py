"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from series2.window import rolling_max


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(rolling_max([], 2), [])

        self.assertEqual(rolling_max([1, 2], 5), [])


if __name__ == "__main__":
    unittest.main()
