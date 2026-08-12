"""Regression checks added with the fix."""

import unittest

from rollup.cohort import cohort_sizes


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(cohort_sizes([{'id': 1, 'cohort': 'c1'}], [{'user_id': 1}]), {'c1': 1})


if __name__ == "__main__":
    unittest.main()
