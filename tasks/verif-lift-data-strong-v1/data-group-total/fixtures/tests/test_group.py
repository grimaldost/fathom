"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.group import total_by


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(total_by([{'r': 'a', 'n': 2}, {'r': 'a', 'n': 3}, {'r': 'b', 'n': 4}], 'r', 'n'), {'a': 5, 'b': 4})


if __name__ == "__main__":
    unittest.main()
