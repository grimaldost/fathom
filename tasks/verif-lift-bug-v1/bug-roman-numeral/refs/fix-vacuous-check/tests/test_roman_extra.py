"""Regression checks added with the fix."""

import unittest

from numerals.roman import to_roman


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(to_roman(3), 'III')

        self.assertEqual(to_roman(2026), 'MMXXVI')

        self.assertEqual(to_roman(15), 'XV')


if __name__ == "__main__":
    unittest.main()
