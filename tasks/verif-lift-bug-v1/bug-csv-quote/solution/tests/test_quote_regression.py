"""Regression checks added with the fix."""

import unittest

from csvlite.quote import quote_field


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(quote_field('say "hi"'), '"say ""hi"""')

        self.assertEqual(quote_field('a,"b"'), '"a,""b"""')


if __name__ == "__main__":
    unittest.main()
