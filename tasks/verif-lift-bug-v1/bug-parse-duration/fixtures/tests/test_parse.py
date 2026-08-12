"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from durationkit.parse import parse_duration


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(parse_duration('1h30m'), 5400)

        self.assertEqual(parse_duration('45s'), 45)


if __name__ == "__main__":
    unittest.main()
