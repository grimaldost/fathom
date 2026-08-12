"""Regression checks added with the fix."""

import unittest

from rollup.group import total_by


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(total_by([{'r': 'a', 'n': 0}], 'r', 'n', strict=True), {'a': 0})
        self.assertEqual(total_by([{'r': 'a', 'n': 3}, {'r': 'b', 'n': 0}], 'r', 'n', strict=True), {'a': 3, 'b': 0})


if __name__ == "__main__":
    unittest.main()
