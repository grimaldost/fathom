"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from tablekit.width import column_widths


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(column_widths(['id'], [['12345']]), [5])

        self.assertEqual(column_widths(['ab'], [['xyz']]), [3])


if __name__ == "__main__":
    unittest.main()
