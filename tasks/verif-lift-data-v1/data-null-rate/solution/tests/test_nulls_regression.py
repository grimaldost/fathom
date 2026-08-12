"""Regression checks added with the fix."""

import unittest

from quality.nulls import null_rate


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(null_rate([{'a': ''}, {'a': 2}], 'a'), 0.5)

        self.assertEqual(null_rate([{'a': '   '}, {'a': None}], 'a'), 1.0)

    def test_related_cases(self):
        self.assertEqual(null_rate([], 'a'), None)


if __name__ == "__main__":
    unittest.main()
