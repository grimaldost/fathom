"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from textkit.wrap import wrap_words


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(wrap_words('one two three', 9), ['one two', 'three'])

        self.assertEqual(wrap_words('a b c', 5), ['a b c'])


if __name__ == "__main__":
    unittest.main()
