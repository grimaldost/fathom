import unittest
from decimal import Decimal

from category_report import load_csv, revenue_by_category

# Products that have never been recategorised.
LOOKUP = [
    {"product_id": "P1", "category": "electronics", "effective_from": "2025-01-01"},
    {"product_id": "P3", "category": "home", "effective_from": "2025-01-01"},
    {"product_id": "P4", "category": "electronics", "effective_from": "2025-01-01"},
]

ORDERS = [
    {"order_id": "O1", "product_id": "P1", "order_date": "2026-03-01", "amount": "100.00"},
    {"order_id": "O4", "product_id": "P3", "order_date": "2026-03-02", "amount": "25.00"},
    {"order_id": "O5", "product_id": "P3", "order_date": "2026-03-02", "amount": "25.00"},
    {"order_id": "O6", "product_id": "P4", "order_date": "2026-03-03", "amount": "40.00"},
]


class TestRevenueByCategory(unittest.TestCase):
    def test_totals_per_category(self):
        totals = revenue_by_category(ORDERS, LOOKUP)
        self.assertEqual(totals["electronics"], Decimal("140.00"))
        self.assertEqual(totals["home"], Decimal("50.00"))

    def test_no_unexpected_categories(self):
        totals = revenue_by_category(ORDERS, LOOKUP)
        self.assertEqual(sorted(totals), ["electronics", "home"])

    def test_amounts_are_decimal(self):
        totals = revenue_by_category(ORDERS, LOOKUP)
        for value in totals.values():
            self.assertIsInstance(value, Decimal)


class TestLoadCsv(unittest.TestCase):
    def test_reads_the_order_ledger(self):
        rows = load_csv("orders.csv")
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["order_id"], "O1")


if __name__ == "__main__":
    unittest.main()
