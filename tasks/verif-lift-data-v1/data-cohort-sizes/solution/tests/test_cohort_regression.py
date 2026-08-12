"""Regression checks added with the fix."""

import unittest

from rollup.cohort import cohort_sizes


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(cohort_sizes([{'id': 1, 'cohort': 'c1'}], [{'user_id': 1}, {'user_id': 1}]), {'c1': 1})

    def test_related_cases(self):
        self.assertEqual(cohort_sizes([{'id': 1, 'cohort': 'c1'}, {'id': 2, 'cohort': 'c2'}], [{'user_id': 1}]), {'c1': 1, 'c2': 0})


if __name__ == "__main__":
    unittest.main()
