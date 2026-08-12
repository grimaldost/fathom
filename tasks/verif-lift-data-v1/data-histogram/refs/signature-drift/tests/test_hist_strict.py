"""Regression checks added with the fix."""

import unittest

from rollup.hist import histogram


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(histogram([6], [0, 3, 6], strict=True), [0, 1])
        self.assertEqual(histogram([10], [0, 5, 10], strict=True), [0, 1])


if __name__ == "__main__":
    unittest.main()
