"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from tablerender.escape import escape_cell, escape_header


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(escape_cell('  plain  '), 'plain')

    def test_shipped_cases_twin(self):
        self.assertEqual(escape_header('  name  '), 'NAME')


if __name__ == "__main__":
    unittest.main()
