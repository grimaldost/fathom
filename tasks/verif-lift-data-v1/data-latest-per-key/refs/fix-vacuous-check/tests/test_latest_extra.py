"""Regression checks added with the fix."""

import unittest

from dedupe.latest import latest_per_key


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(latest_per_key([{'k': 'a', 'ts': 1, 'v': 'old'}, {'k': 'a', 'ts': 2, 'v': 'new'}], 'k'), [{'k': 'a', 'ts': 2, 'v': 'new'}])


if __name__ == "__main__":
    unittest.main()
