"""Regression checks added with the fix."""

import unittest

from textkit.title import title_case


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(title_case('well-known issue'), 'Well-Known Issue')

        self.assertEqual(title_case('up-to-date'), 'Up-To-Date')


if __name__ == "__main__":
    unittest.main()
