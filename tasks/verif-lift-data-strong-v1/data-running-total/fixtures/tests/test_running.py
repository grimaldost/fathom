"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.running import running_total


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(running_total([1, 2, 3]), [1.0, 3.0, 6.0])

        self.assertEqual(running_total([]), [])


if __name__ == "__main__":
    unittest.main()
