"""Regression checks added with the fix."""

import unittest

from durationkit.parse import parse_duration


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(parse_duration('0h5m'), 300)

        with self.assertRaises(ValueError):
            parse_duration('')


if __name__ == "__main__":
    unittest.main()
