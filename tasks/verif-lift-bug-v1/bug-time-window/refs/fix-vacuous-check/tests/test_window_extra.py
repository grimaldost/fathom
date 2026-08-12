"""Regression checks added with the fix."""

import unittest

from sched.window import slots


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(slots(0, 25, 10), [0, 10])

        self.assertEqual(slots(0, 5, 10), [])


if __name__ == "__main__":
    unittest.main()
