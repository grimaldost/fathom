import unittest
from datetime import date
from decimal import Decimal

from reconcile import reconcile

ORDER_ROWS = [
    {"region": "north", "period": date(2026, 3, 2), "gross_amount": Decimal("150.00")},
    {"region": "south", "period": date(2026, 3, 3), "gross_amount": Decimal("80.00")},
    {"region": "east", "period": date(2026, 3, 3), "gross_amount": Decimal("10.00")},
]

SETTLEMENT_ROWS = [
    {"region": "north", "period": date(2026, 3, 2), "settled_amount": Decimal("150.00")},
    {"region": "south", "period": date(2026, 3, 3), "settled_amount": Decimal("80.00")},
]


class TestReconcile(unittest.TestCase):
    def test_joins_on_region_and_period(self):
        rows = reconcile(ORDER_ROWS, SETTLEMENT_ROWS)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["region"], "north")
        self.assertEqual(rows[0]["settled_amount"], Decimal("150.00"))

    def test_drops_periods_with_no_settlement(self):
        rows = reconcile(ORDER_ROWS, SETTLEMENT_ROWS)
        self.assertNotIn("east", [row["region"] for row in rows])

    def test_carries_both_amounts(self):
        rows = reconcile(ORDER_ROWS, SETTLEMENT_ROWS)
        for row in rows:
            self.assertIn("gross_amount", row)
            self.assertIn("settled_amount", row)


if __name__ == "__main__":
    unittest.main()
