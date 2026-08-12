"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from dedupe.latest import latest_per_key


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(latest_per_key([{'k': 'a', 'ts': 1, 'v': 'old'}, {'k': 'a', 'ts': 2, 'v': 'new'}], 'k'), [{'k': 'a', 'ts': 2, 'v': 'new'}])


if __name__ == "__main__":
    unittest.main()
