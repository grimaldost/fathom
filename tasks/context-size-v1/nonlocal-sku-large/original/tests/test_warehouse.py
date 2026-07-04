import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from warehouse.inventory import stock_for
from warehouse.pricing import price_for


class TestWarehouse(unittest.TestCase):
    def test_exact_stock(self):
        self.assertEqual(stock_for("WIDGET", [("WIDGET", 5)]), 5)

    def test_exact_price(self):
        self.assertEqual(price_for("GADGET", {"GADGET": 200}), 200)


if __name__ == "__main__":
    unittest.main()
