"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from textkit.title import title_case


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(title_case('hello world'), 'Hello World')

        self.assertEqual(title_case('a b'), 'A B')


if __name__ == "__main__":
    unittest.main()
