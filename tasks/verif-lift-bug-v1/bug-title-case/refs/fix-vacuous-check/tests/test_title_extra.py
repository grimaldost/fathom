"""Regression checks added with the fix."""

import unittest

from textkit.title import title_case


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(title_case('hello world'), 'Hello World')

        self.assertEqual(title_case('a b'), 'A B')


if __name__ == "__main__":
    unittest.main()
