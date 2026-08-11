"""Regression checks added with the fix."""

import unittest

from durationkit.parse import parse_duration


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(parse_duration('1h30m'), 5400)

        self.assertEqual(parse_duration('45s'), 45)


if __name__ == "__main__":
    unittest.main()
