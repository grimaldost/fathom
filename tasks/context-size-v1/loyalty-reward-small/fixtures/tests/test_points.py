import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewards.points import reward


class TestPoints(unittest.TestCase):
    def test_returns_decimal(self):
        self.assertIsInstance(reward("c_silver", Decimal("100")), Decimal)

    def test_zero_spend_zero_reward(self):
        self.assertEqual(reward("c_gold", Decimal("0")), Decimal("0"))

    def test_silver_base_rate(self):
        self.assertEqual(reward("c_silver", Decimal("100")), Decimal("1.00"))


if __name__ == "__main__":
    unittest.main()
