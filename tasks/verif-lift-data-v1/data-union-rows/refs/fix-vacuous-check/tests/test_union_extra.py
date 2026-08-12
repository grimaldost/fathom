"""Regression checks added with the fix."""

import unittest

from setops.union import union_rows


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(union_rows([{'id': 1, 'v': 'a'}], [{'id': 1, 'v': 'a'}], 'id'), [{'id': 1, 'v': 'a'}])


if __name__ == "__main__":
    unittest.main()
