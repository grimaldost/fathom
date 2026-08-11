import unittest
from datetime import date

from daycal.report import hours_in_day


class TestTransitions(unittest.TestCase):
    def test_the_short_day(self):
        self.assertEqual(hours_in_day(date(2026, 3, 8)), 23.0)


if __name__ == "__main__":
    unittest.main()
