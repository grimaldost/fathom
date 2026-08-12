"""Regression checks added with the fix."""

import unittest

from joinkit.left import left_join


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(left_join([{'id': 1}], [{'id': 1, 'tag': 'x'}, {'id': 1, 'tag': 'y'}], 'id'), [{'id': 1, 'tag': 'x'}, {'id': 1, 'tag': 'y'}])

    def test_related_cases(self):
        self.assertEqual(left_join([{'id': 1, 'tag': 'L'}], [{'id': 1, 'tag': 'x'}], 'id'), [{'id': 1, 'tag': 'L'}])

        self.assertEqual(left_join([{'id': 1, 'tag': 'L'}], [{'id': 1, 'tag': 'x'}, {'id': 1, 'tag': 'y'}], 'id'), [{'id': 1, 'tag': 'L'}, {'id': 1, 'tag': 'L'}])


if __name__ == "__main__":
    unittest.main()
