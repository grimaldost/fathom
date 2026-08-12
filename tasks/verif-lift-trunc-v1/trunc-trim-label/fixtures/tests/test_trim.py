"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from labels.trim import trim_label, trim_note


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(trim_label('short', 10), 'short')

    def test_shipped_cases_twin(self):
        self.assertEqual(trim_note('ok', 10), 'ok')


if __name__ == "__main__":
    unittest.main()
