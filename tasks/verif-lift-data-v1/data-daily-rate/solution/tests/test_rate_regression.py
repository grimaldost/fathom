"""Regression checks added with the fix."""

import unittest

from rollup.rate import daily_rate


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(daily_rate([{'day': 'd1', 'events': 0, 'actors': 0}]), {'d1': None})

        self.assertEqual(daily_rate([{'day': 'd1', 'events': 7, 'actors': 0}]), {'d1': None})

    def test_related_cases(self):
        self.assertEqual(daily_rate([{'day': 'd1', 'events': 3, 'actors': 0}, {'day': 'd2', 'events': 6, 'actors': 3}]), {'d1': None, 'd2': 2.0})


if __name__ == "__main__":
    unittest.main()
