import unittest

from money import fast


class TestHalfUp(unittest.TestCase):
    def test_positive_ties_round_away_from_zero(self):
        self.assertEqual(fast.round_half_up(0.5), 1.0)
        self.assertEqual(fast.round_half_up(0.125, 2), 0.13)


if __name__ == "__main__":
    unittest.main()
