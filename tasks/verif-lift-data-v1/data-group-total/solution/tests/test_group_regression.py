"""Regression checks added with the fix."""

import unittest

from rollup.group import total_by


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(total_by([{'r': 'a', 'n': 0}], 'r', 'n'), {'a': 0})

        self.assertEqual(total_by([{'r': 'a', 'n': 3}, {'r': 'b', 'n': 0}], 'r', 'n'), {'a': 3, 'b': 0})

    def test_related_cases(self):
        with self.assertRaises(KeyError):
            total_by([{'r': 'a', 'm': 1}], 'r', 'n')

        with self.assertRaises(KeyError):
            total_by([{'r': 'a', 'n': 2}, {'r': 'b'}], 'r', 'n')


if __name__ == "__main__":
    unittest.main()
