"""Regression checks added with the fix."""

import unittest

from dedupe.latest import latest_per_key


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(latest_per_key([{'k': 'a', 'ts': 5, 'v': 'first'}, {'k': 'a', 'ts': 5, 'v': 'second'}], 'k'), [{'k': 'a', 'ts': 5, 'v': 'second'}])

    def test_related_cases(self):
        self.assertEqual(latest_per_key([{'k': 'a', 'ts': 3, 'v': 'x'}, {'k': 'b', 'ts': 3, 'v': 'y'}, {'k': 'b', 'ts': 3, 'v': 'z'}], 'k'), [{'k': 'a', 'ts': 3, 'v': 'x'}, {'k': 'b', 'ts': 3, 'v': 'z'}])


if __name__ == "__main__":
    unittest.main()
