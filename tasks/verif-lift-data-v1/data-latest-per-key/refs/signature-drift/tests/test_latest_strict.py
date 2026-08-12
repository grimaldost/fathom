"""Regression checks added with the fix."""

import unittest

from dedupe.latest import latest_per_key


class RegressionChecks(unittest.TestCase):
    def test_strict_mode(self):
        self.assertEqual(latest_per_key([{'k': 'a', 'ts': 5, 'v': 'first'}, {'k': 'a', 'ts': 5, 'v': 'second'}], 'k', strict=True), [{'k': 'a', 'ts': 5, 'v': 'second'}])


if __name__ == "__main__":
    unittest.main()
