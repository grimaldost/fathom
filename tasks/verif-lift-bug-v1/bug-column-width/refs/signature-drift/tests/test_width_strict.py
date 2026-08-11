"""Regression checks added with the fix."""

import unittest

from tablekit.width import column_widths


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(column_widths(['identifier'], [['12']], strict=True), [10])
        self.assertEqual(column_widths(['a', 'region'], [['xx', 'eu']], strict=True), [2, 6])


if __name__ == "__main__":
    unittest.main()
