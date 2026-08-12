"""Regression checks added with the fix."""

import unittest

from rollup.group import total_by


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(total_by([{'r': 'a', 'n': 2}, {'r': 'a', 'n': 3}, {'r': 'b', 'n': 4}], 'r', 'n'), {'a': 5, 'b': 4})


if __name__ == "__main__":
    unittest.main()
