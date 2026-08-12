"""Regression checks added with the fix."""

import unittest

from numerals.base import to_base


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(to_base(10, 2), '1010')

        self.assertEqual(to_base(255, 16), 'ff')

        self.assertEqual(to_base(7, 8), '7')


if __name__ == "__main__":
    unittest.main()
