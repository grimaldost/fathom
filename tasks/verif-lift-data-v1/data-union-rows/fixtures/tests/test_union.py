"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from setops.union import union_rows


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(union_rows([{'id': 1, 'v': 'a'}], [{'id': 1, 'v': 'a'}], 'id'), [{'id': 1, 'v': 'a'}])


if __name__ == "__main__":
    unittest.main()
