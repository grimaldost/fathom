"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from retrykit.backoff import delays


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(delays(3, 1.0), [1.0, 2.0])

        self.assertEqual(delays(1, 1.0), [])


if __name__ == "__main__":
    unittest.main()
