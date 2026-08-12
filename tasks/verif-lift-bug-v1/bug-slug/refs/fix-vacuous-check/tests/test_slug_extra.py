"""Regression checks added with the fix."""

import unittest

from textkit.slug import slugify


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(slugify('Hello World'), 'hello-world')

        self.assertEqual(slugify('  edges  '), 'edges')


if __name__ == "__main__":
    unittest.main()
