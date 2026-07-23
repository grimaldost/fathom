import unittest
from decimal import Decimal

from enrich import load_rows, revenue_by_region


class TestEnrich(unittest.TestCase):
    def setUp(self):
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        orders = load_rows(root / "orders.csv")
        customers = load_rows(root / "customers.csv")
        self.totals = revenue_by_region(orders, customers)

    def test_north_revenue(self):
        self.assertEqual(self.totals["North"], Decimal("170.00"))


if __name__ == "__main__":
    unittest.main()
