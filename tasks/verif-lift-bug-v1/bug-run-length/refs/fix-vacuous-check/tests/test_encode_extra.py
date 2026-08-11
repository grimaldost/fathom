"""Regression checks added with the fix."""

import unittest

from rlekit.encode import encode_runs


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(encode_runs(''), [])


if __name__ == "__main__":
    unittest.main()
