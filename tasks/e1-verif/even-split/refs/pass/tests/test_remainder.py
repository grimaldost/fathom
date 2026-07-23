import unittest

from allocate import split_amount


class TestRemainderDistribution(unittest.TestCase):
    def test_indivisible_shares_sum_to_total(self):
        shares = split_amount(100, 3)
        self.assertEqual(shares, [34, 33, 33])
        self.assertEqual(sum(shares), 100)

    def test_leftover_goes_to_earliest_shares(self):
        self.assertEqual(split_amount(103, 4), [26, 26, 26, 25])

    def test_small_indivisible_case(self):
        shares = split_amount(7, 2)
        self.assertEqual(shares, [4, 3])
        self.assertEqual(sum(shares), 7)


if __name__ == "__main__":
    unittest.main()
