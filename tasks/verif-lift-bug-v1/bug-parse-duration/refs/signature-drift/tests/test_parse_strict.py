"""Regression checks added with the fix."""

import unittest

from durationkit.parse import parse_duration


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(parse_duration('0h5m', strict=True), 300)
        with self.assertRaises(ValueError):
            parse_duration('', strict=True)


if __name__ == "__main__":
    unittest.main()
