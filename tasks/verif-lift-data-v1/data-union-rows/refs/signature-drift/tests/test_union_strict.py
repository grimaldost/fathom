"""Regression checks added with the fix."""

import unittest

from setops.union import union_rows


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(union_rows([{'id': 1, 'v': 'a'}], [{'id': 1, 'v': 'b'}], 'id', strict=True), [{'id': 1, 'v': 'a'}])


if __name__ == "__main__":
    unittest.main()
