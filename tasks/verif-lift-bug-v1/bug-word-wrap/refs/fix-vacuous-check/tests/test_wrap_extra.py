"""Regression checks added with the fix."""

import unittest

from textkit.wrap import wrap_words


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(wrap_words('one two three', 9), ['one two', 'three'])

        self.assertEqual(wrap_words('a b c', 5), ['a b c'])


if __name__ == "__main__":
    unittest.main()
