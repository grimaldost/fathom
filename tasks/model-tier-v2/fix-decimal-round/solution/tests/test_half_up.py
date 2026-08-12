import unittest

from money import exact, fast
from money.total import line_total


class TestHalfUp(unittest.TestCase):
    def test_positive_ties_round_away_from_zero(self):
        self.assertEqual(fast.round_half_up(0.5), 1.0)
        self.assertEqual(fast.round_half_up(0.125, 2), 0.13)

    def test_negative_ties_round_away_from_zero(self):
        self.assertEqual(fast.round_half_up(-0.5), -1.0)
        self.assertEqual(fast.round_half_up(-0.125, 2), -0.13)

    def test_the_backends_agree_on_a_decimal_literal(self):
        self.assertEqual(fast.round_half_up(2.675, 2), exact.round_half_up(2.675, 2))
        self.assertEqual(line_total(1, 2.675, "fast"), line_total(1, 2.675, "exact"))


if __name__ == "__main__":
    unittest.main()
