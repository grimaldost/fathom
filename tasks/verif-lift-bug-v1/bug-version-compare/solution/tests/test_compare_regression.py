"""Regression checks added with the fix."""

import unittest

from semver2.compare import compare_versions


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(compare_versions('1.10.0', '1.9.0'), 1)

        self.assertEqual(compare_versions('2.0.0', '10.0.0'), -1)


if __name__ == "__main__":
    unittest.main()
