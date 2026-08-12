"""Regression checks added with the fix."""

import unittest

from pathkit.norm import normalize


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(normalize('a/./b/c'), 'a/b/c')

        self.assertEqual(normalize('a/../b/c'), 'b/c')


if __name__ == "__main__":
    unittest.main()
