"""Regression checks added with the fix."""

import unittest

from retrykit.backoff import delays


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(delays(3, 1.0), [1.0, 2.0])

        self.assertEqual(delays(1, 1.0), [])


if __name__ == "__main__":
    unittest.main()
