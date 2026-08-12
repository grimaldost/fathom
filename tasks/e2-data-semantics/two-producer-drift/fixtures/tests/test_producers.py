import unittest
from decimal import Decimal

from producers import orders_producer, settlements_producer

RAW_ORDERS = [
    {"region": "north", "order_date": "2026-03-02", "amount": "120.00"},
    {"region": "north", "order_date": "2026-03-02", "amount": "30.00"},
    {"region": "south", "order_date": "2026-03-03", "amount": "80.00"},
]

RAW_SETTLEMENTS = [
    {"region": "north", "settled_at": "2026-03-02", "amount": "150.00", "source": "batch"},
    {
        "region": "south",
        "settled_at": "2026-03-03T14:05:00",
        "amount": "80.00",
        "source": "streaming",
    },
]


class TestOrdersProducer(unittest.TestCase):
    def test_aggregates_by_region_and_day(self):
        rows = orders_producer.emit(RAW_ORDERS)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["region"], "north")
        self.assertEqual(rows[0]["gross_amount"], Decimal("150.00"))

    def test_period_is_the_order_day(self):
        rows = orders_producer.emit(RAW_ORDERS)
        self.assertEqual(rows[0]["period"].year, 2026)
        self.assertEqual(rows[0]["period"].month, 3)
        self.assertEqual(rows[0]["period"].day, 2)


class TestSettlementsProducer(unittest.TestCase):
    def test_aggregates_by_region_and_day(self):
        rows = settlements_producer.emit(RAW_SETTLEMENTS)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["settled_amount"], Decimal("150.00"))

    def test_period_is_the_settlement_day(self):
        rows = settlements_producer.emit(RAW_SETTLEMENTS)
        for row in rows:
            self.assertEqual(row["period"].year, 2026)
            self.assertEqual(row["period"].month, 3)
        self.assertEqual(rows[0]["period"].day, 2)
        self.assertEqual(rows[1]["period"].day, 3)


if __name__ == "__main__":
    unittest.main()
