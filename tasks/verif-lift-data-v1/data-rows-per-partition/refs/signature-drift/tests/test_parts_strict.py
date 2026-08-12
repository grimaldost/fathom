"""Regression checks added with the fix."""

import unittest

from rollup.parts import rows_per_partition


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(rows_per_partition([{'partition': None}], ['p1'], strict=True), {'p1': 0, '__unpartitioned__': 1})


if __name__ == "__main__":
    unittest.main()
