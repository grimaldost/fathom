"""Regression checks added with the fix."""

import unittest

from rollup.rate import daily_rate


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(daily_rate([{'day': 'd1', 'events': 0, 'actors': 0}], strict=True), {'d1': None})
        self.assertEqual(daily_rate([{'day': 'd1', 'events': 7, 'actors': 0}], strict=True), {'d1': None})


if __name__ == "__main__":
    unittest.main()
