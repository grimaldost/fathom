"""Regression checks added with the fix."""

import unittest

from rollup.topk import top_k


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(top_k([{'name': 'z', 'score': 5}, {'name': 'a', 'score': 5}], 2), [{'name': 'a', 'score': 5}, {'name': 'z', 'score': 5}])

    def test_related_cases(self):
        self.assertEqual(top_k([{'name': 'm', 'score': 4}, {'name': 'b', 'score': 7}, {'name': 'a', 'score': 4}], 3), [{'name': 'b', 'score': 7}, {'name': 'a', 'score': 4}, {'name': 'm', 'score': 4}])


if __name__ == "__main__":
    unittest.main()
