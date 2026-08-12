"""Regression checks added with the fix."""

import unittest

from rlekit.encode import encode_runs


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(encode_runs('aaabb'), [['a', 3], ['b', 2]])

        self.assertEqual(encode_runs('x'), [['x', 1]])


if __name__ == "__main__":
    unittest.main()
