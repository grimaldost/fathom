"""Regression checks added with the fix."""

import unittest

from validate2.luhn import is_valid


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(is_valid('18'), True)

        self.assertEqual(is_valid('1230'), True)

        self.assertEqual(is_valid('4539578763621486'), True)


if __name__ == "__main__":
    unittest.main()
