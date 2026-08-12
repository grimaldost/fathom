"""Regression checks added with the fix."""

import unittest

from semver2.compare import compare_versions


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(compare_versions('1.2.3', '1.2.3'), 0)

        self.assertEqual(compare_versions('1.2.3', '1.3.0'), -1)


if __name__ == "__main__":
    unittest.main()
