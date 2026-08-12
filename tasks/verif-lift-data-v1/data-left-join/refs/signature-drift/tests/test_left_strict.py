"""Regression checks added with the fix."""

import unittest

from joinkit.left import left_join


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(left_join([{'id': 1}], [{'id': 1, 'tag': 'x'}, {'id': 1, 'tag': 'y'}], 'id', strict=True), [{'id': 1, 'tag': 'x'}, {'id': 1, 'tag': 'y'}])


if __name__ == "__main__":
    unittest.main()
