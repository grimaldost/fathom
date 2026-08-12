"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from cleanse.keys import normalize_keys


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(normalize_keys([{'k': ' abc '}], 'k'), [{'k': 'abc'}])


if __name__ == "__main__":
    unittest.main()
