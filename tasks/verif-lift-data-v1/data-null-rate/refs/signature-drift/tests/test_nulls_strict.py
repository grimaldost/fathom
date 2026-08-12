"""Regression checks added with the fix."""

import unittest

from quality.nulls import null_rate


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(null_rate([{'a': ''}, {'a': 2}], 'a', strict=True), 0.5)
        self.assertEqual(null_rate([{'a': '   '}, {'a': None}], 'a', strict=True), 1.0)


if __name__ == "__main__":
    unittest.main()
