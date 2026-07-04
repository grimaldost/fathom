import unittest

from timeflow.parser import normalize, parse_timestamp


class TestParser(unittest.TestCase):
    def test_normalize_z(self):
        self.assertEqual(normalize("2026-06-13T12:00:00Z"), "2026-06-13T12:00:00Z")

    def test_normalize_offset(self):
        self.assertEqual(normalize("2026-06-13T14:00:00+02:00"), "2026-06-13T12:00:00Z")

    def test_parse_naive_assumes_utc(self):
        self.assertEqual(parse_timestamp("2026-06-13T12:00:00").hour, 12)


if __name__ == "__main__":
    unittest.main()
