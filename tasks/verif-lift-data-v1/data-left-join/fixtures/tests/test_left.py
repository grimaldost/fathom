"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from joinkit.left import left_join


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(left_join([{'id': 1}], [{'id': 1, 'tag': 'x'}], 'id'), [{'id': 1, 'tag': 'x'}])


if __name__ == "__main__":
    unittest.main()
