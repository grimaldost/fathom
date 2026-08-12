import unittest

from mathkit.rounding import places_needed, round_to


class RoundingTests(unittest.TestCase):
    def test_round_half_away_from_zero(self):
        self.assertEqual(round_to(2.5, 0), 3.0)
        self.assertEqual(round_to(-2.5, 0), -3.0)

    def test_places_needed(self):
        self.assertEqual(places_needed(1.25), 2)


if __name__ == "__main__":
    unittest.main()
