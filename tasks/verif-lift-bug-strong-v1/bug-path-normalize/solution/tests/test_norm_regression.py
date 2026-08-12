"""Regression checks added with the fix."""

import unittest

from pathkit.norm import normalize


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(normalize('a/b/..'), 'a')

        self.assertEqual(normalize('a/b/c/../..'), 'a')


if __name__ == "__main__":
    unittest.main()
