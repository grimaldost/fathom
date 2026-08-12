"""Regression checks added with the fix."""

import unittest

from textkit.ordinal import ordinal


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(ordinal(1), '1st')

        self.assertEqual(ordinal(22), '22nd')

        self.assertEqual(ordinal(5), '5th')


if __name__ == "__main__":
    unittest.main()
