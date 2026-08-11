"""Regression checks added with the fix."""

import unittest

from retrykit.backoff import delays


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(delays(8, 1.0, strict=True), [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0])
        self.assertEqual(delays(7, 5.0, strict=True), [5.0, 10.0, 20.0, 30.0, 30.0, 30.0])


if __name__ == "__main__":
    unittest.main()
