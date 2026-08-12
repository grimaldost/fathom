"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from quality.nulls import null_rate


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(null_rate([{'a': 1}, {'a': None}], 'a'), 0.5)

        self.assertEqual(null_rate([{'a': 1}, {'a': 2}], 'a'), 0.0)


if __name__ == "__main__":
    unittest.main()
