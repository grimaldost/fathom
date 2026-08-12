"""Regression checks added with the fix."""

import unittest

from series2.fill import forward_fill


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(forward_fill([None, 3], strict=True), [None, 3])
        self.assertEqual(forward_fill([None, None, 7], strict=True), [None, None, 7])


if __name__ == "__main__":
    unittest.main()
