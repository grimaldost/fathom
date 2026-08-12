"""Regression checks added with the fix."""

import unittest

from numerals.base import to_base


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(to_base(0, 2), '0')

        self.assertEqual(to_base(0, 16), '0')


if __name__ == "__main__":
    unittest.main()
