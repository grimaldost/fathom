import unittest

from money import exact, fast
from money.total import line_total


class TestRounding(unittest.TestCase):
    def test_values_that_are_not_ties(self):
        self.assertEqual(fast.round_half_up(2.4), 2.0)
        self.assertEqual(fast.round_half_up(2.6), 3.0)
        self.assertEqual(fast.round_half_up(2.34, 2), 2.34)

    def test_both_backends_agree_away_from_a_tie(self):
        for value in (2.4, 2.6, -2.4, -2.6, 0.0):
            self.assertEqual(fast.round_half_up(value), exact.round_half_up(value))

    def test_line_total_uses_two_places(self):
        self.assertEqual(line_total(2, 1.1), 2.2)


if __name__ == "__main__":
    unittest.main()
