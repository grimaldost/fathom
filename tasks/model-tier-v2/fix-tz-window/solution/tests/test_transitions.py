import unittest
from datetime import date, timedelta

from daycal.report import hours_in_day, slots
from daycal.window import day_window, local_midnight_utc

SHORT_DAY = date(2026, 3, 8)
LONG_DAY = date(2026, 11, 1)


class TestTransitions(unittest.TestCase):
    def test_short_and_long_days(self):
        self.assertEqual(hours_in_day(SHORT_DAY), 23.0)
        self.assertEqual(hours_in_day(LONG_DAY), 25.0)

    def test_window_ends_at_the_next_local_midnight(self):
        for day in (SHORT_DAY, LONG_DAY, date(2026, 6, 15)):
            self.assertEqual(day_window(day)[1], local_midnight_utc(day + timedelta(days=1)))

    def test_slots_cover_a_transition_day(self):
        parts = slots(SHORT_DAY, 4)
        self.assertEqual(parts[0][0], local_midnight_utc(SHORT_DAY))
        self.assertEqual(parts[-1][1], local_midnight_utc(SHORT_DAY + timedelta(days=1)))


if __name__ == "__main__":
    unittest.main()
