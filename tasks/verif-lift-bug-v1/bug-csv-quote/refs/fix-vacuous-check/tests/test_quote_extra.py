"""Regression checks added with the fix."""

import unittest

from csvlite.quote import quote_field


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(quote_field('plain'), 'plain')

        self.assertEqual(quote_field('a,b'), '"a,b"')


if __name__ == "__main__":
    unittest.main()
