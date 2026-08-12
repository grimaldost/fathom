"""Regression checks added with the fix."""

import unittest

from quality.nulls import null_rate


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(null_rate([{'a': 1}, {'a': None}], 'a'), 0.5)

        self.assertEqual(null_rate([{'a': 1}, {'a': 2}], 'a'), 0.0)


if __name__ == "__main__":
    unittest.main()
