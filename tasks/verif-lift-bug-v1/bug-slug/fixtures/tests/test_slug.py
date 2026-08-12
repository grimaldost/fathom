"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from textkit.slug import slugify


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(slugify('Hello World'), 'hello-world')

        self.assertEqual(slugify('  edges  '), 'edges')


if __name__ == "__main__":
    unittest.main()
