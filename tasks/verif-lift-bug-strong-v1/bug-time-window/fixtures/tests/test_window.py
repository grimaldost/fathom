"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from sched.window import slots


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(slots(0, 25, 10), [0, 10])

        self.assertEqual(slots(0, 5, 10), [])


if __name__ == "__main__":
    unittest.main()
