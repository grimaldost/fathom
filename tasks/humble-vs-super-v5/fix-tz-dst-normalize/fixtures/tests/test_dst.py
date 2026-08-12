import unittest

from eastern.dst import to_utc


class TestEasternToUtc(unittest.TestCase):
    def test_winter_is_est(self):
        # January is unambiguously standard time (UTC-5).
        self.assertEqual(to_utc(2026, 1, 15, 12, 0), "2026-01-15T17:00:00Z")

    def test_summer_is_edt(self):
        # July is unambiguously daylight saving time (UTC-4).
        self.assertEqual(to_utc(2026, 7, 15, 12, 0), "2026-07-15T16:00:00Z")

    def test_default_minute(self):
        self.assertEqual(to_utc(2026, 7, 15, 12), "2026-07-15T16:00:00Z")


if __name__ == "__main__":
    unittest.main()
