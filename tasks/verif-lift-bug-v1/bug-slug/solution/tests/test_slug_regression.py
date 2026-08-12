"""Regression checks added with the fix."""

import unittest

from textkit.slug import slugify


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(slugify('a -- b'), 'a-b')

        self.assertEqual(slugify('Report: Q3, final'), 'report-q3-final')


if __name__ == "__main__":
    unittest.main()
