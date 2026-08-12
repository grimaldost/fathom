"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rlekit.encode import encode_runs


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(encode_runs(''), [])


if __name__ == "__main__":
    unittest.main()
