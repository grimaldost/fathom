"""Regression checks added with the fix."""

import unittest

from rollup.medgroup import median_by


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(median_by([{'g': 'a', 'value': 1}, {'g': 'a', 'value': 2}, {'g': 'a', 'value': 9}], 'g'), {'a': 2.0})

    def test_related_cases(self):
        self.assertEqual(median_by([{'g': 'a', 'value': 1}, {'g': 'a', 'value': None}, {'g': 'a', 'value': 3}], 'g'), {'a': 2.0})

        self.assertEqual(median_by([{'g': 'a', 'value': None}], 'g'), {'a': None})


if __name__ == "__main__":
    unittest.main()
