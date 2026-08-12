"""Regression checks added with the fix."""

import unittest

from series2.fill import forward_fill


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(forward_fill([None, 3]), [None, 3])

        self.assertEqual(forward_fill([None, None, 7]), [None, None, 7])

    def test_related_cases(self):
        self.assertEqual(forward_fill([None]), [None])

        self.assertEqual(forward_fill([None, None]), [None, None])


if __name__ == "__main__":
    unittest.main()
