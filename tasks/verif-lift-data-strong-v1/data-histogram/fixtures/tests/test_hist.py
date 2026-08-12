"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.hist import histogram


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(histogram([1, 2, 5], [0, 3, 6]), [2, 1])

        self.assertEqual(histogram([], [0, 1]), [0])


if __name__ == "__main__":
    unittest.main()
