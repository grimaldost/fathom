"""Regression checks added with the fix."""

import unittest

from numerals.roman import to_roman


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(to_roman(4), 'IV')

        self.assertEqual(to_roman(9), 'IX')

        self.assertEqual(to_roman(1944), 'MCMXLIV')


if __name__ == "__main__":
    unittest.main()
