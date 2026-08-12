"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from semver2.compare import compare_versions


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(compare_versions('1.2.3', '1.2.3'), 0)

        self.assertEqual(compare_versions('1.2.3', '1.3.0'), -1)


if __name__ == "__main__":
    unittest.main()
