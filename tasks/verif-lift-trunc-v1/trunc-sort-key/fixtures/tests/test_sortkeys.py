"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from ordering.sortkeys import sort_key_name, sort_key_group


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(sort_key_name('beta'), 'beta')

        self.assertEqual(sort_key_name('   '), '\uffff')

    def test_shipped_cases_twin(self):
        self.assertEqual(sort_key_group('west'), 'west')

        self.assertEqual(sort_key_group(''), '\uffff')


if __name__ == "__main__":
    unittest.main()
