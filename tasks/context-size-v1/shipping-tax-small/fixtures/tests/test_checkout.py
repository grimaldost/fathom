import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shopcart.checkout import grand_total


class TestCheckout(unittest.TestCase):
    def test_returns_decimal(self):
        self.assertIsInstance(grand_total(Decimal("10")), Decimal)

    def test_total_increases_with_subtotal(self):
        self.assertGreater(grand_total(Decimal("100")), grand_total(Decimal("90")))


if __name__ == "__main__":
    unittest.main()
