"""Regression checks added with the fix."""

import unittest

from validate2.luhn import is_valid


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(is_valid('22'), False)

        self.assertEqual(is_valid('1111'), False)

        self.assertEqual(is_valid('79927398710'), False)


if __name__ == "__main__":
    unittest.main()
