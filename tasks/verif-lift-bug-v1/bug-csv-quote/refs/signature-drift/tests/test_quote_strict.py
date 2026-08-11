"""Regression checks added with the fix."""

import unittest

from csvlite.quote import quote_field


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(quote_field('say "hi"', strict=True), '"say ""hi"""')
        self.assertEqual(quote_field('a,"b"', strict=True), '"a,""b"""')


if __name__ == "__main__":
    unittest.main()
