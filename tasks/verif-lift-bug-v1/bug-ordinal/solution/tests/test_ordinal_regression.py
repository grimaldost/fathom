"""Regression checks added with the fix."""

import unittest

from textkit.ordinal import ordinal


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(ordinal(11), '11th')

        self.assertEqual(ordinal(12), '12th')

        self.assertEqual(ordinal(113), '113th')


if __name__ == "__main__":
    unittest.main()
