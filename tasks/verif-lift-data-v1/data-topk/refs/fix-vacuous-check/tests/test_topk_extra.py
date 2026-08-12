"""Regression checks added with the fix."""

import unittest

from rollup.topk import top_k


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(top_k([{'name': 'a', 'score': 3}, {'name': 'b', 'score': 9}], 1), [{'name': 'b', 'score': 9}])


if __name__ == "__main__":
    unittest.main()
