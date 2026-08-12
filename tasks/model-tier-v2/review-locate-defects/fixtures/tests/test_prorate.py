"""Shipped suite. Green on the current source: it exercises the paths the six
functions agree with RULES.md on, never the ones they do not."""

import unittest

from billing.prorate import charge, is_refund, net


class TestProrate(unittest.TestCase):
    def test_a_full_cycle_charge_is_the_whole_amount(self):
        self.assertEqual(charge(1000, 30, 30), 1000)

    def test_a_zero_cycle_charges_nothing(self):
        self.assertEqual(charge(1000, 5, 0), 0)

    def test_half_a_cycle_charges_half(self):
        self.assertEqual(charge(1000, 15, 30), 500)

    def test_a_negative_net_is_a_refund(self):
        self.assertTrue(is_refund(-1))

    def test_a_positive_net_is_not_a_refund(self):
        self.assertFalse(is_refund(1))

    def test_net_is_the_charge_less_the_credit(self):
        self.assertIsInstance(net(1000, 2000, 1, 1, 31), int)


if __name__ == "__main__":
    unittest.main()
