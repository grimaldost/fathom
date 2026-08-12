"""Regression checks added with the fix."""

import unittest

from setops.union import union_rows


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(union_rows([{'id': 1, 'v': 'a'}], [{'id': 1, 'v': 'b'}], 'id'), [{'id': 1, 'v': 'a'}])

    def test_related_cases(self):
        self.assertEqual(union_rows([{'id': 1, 'v': 'a'}, {'id': 1, 'v': 'b'}], [], 'id'), [{'id': 1, 'v': 'a'}])

        self.assertEqual(union_rows([], [{'id': 2, 'v': 'x'}, {'id': 2, 'v': 'y'}], 'id'), [{'id': 2, 'v': 'x'}])


if __name__ == "__main__":
    unittest.main()
