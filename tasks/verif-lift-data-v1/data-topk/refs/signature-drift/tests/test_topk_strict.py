"""Regression checks added with the fix."""

import unittest

from rollup.topk import top_k


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(top_k([{'name': 'z', 'score': 5}, {'name': 'a', 'score': 5}], 2, strict=True), [{'name': 'a', 'score': 5}, {'name': 'z', 'score': 5}])


if __name__ == "__main__":
    unittest.main()
