import unittest
from datetime import date

from daycal.report import hours_in_day, slots
from daycal.window import day_window, local_midnight_utc

ORDINARY = date(2026, 6, 15)


class TestReport(unittest.TestCase):
    def test_an_ordinary_day_is_twenty_four_hours(self):
        self.assertEqual(hours_in_day(ORDINARY), 24.0)

    def test_slots_cover_the_window_of_an_ordinary_day(self):
        start, end = day_window(ORDINARY)
        parts = slots(ORDINARY, 4)
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0][0], start)
        self.assertEqual(parts[-1][1], end)

    def test_local_midnight_uses_the_offset_of_the_day(self):
        self.assertEqual(local_midnight_utc(ORDINARY), ORDINARY.toordinal() * 1440 + 240)


if __name__ == "__main__":
    unittest.main()
