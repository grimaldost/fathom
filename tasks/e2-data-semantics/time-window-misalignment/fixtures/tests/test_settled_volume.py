import unittest
from decimal import Decimal

from settled_volume import monthly_volume

ORDERS = [
    {
        "order_id": "T1",
        "event_ts": "2026-03-05T09:00:00+00:00",
        "load_date": "2026-03-05",
        "amount_local": "100.00",
        "currency": "EUR",
    },
    {
        "order_id": "T2",
        "event_ts": "2026-03-06T09:00:00+00:00",
        "load_date": "2026-03-06",
        "amount_local": "200.00",
        "currency": "EUR",
    },
    {
        "order_id": "T3",
        "event_ts": "2026-04-06T09:00:00+00:00",
        "load_date": "2026-04-06",
        "amount_local": "900.00",
        "currency": "EUR",
    },
]

FX_RATES = [
    {"rate_date": "2026-03-05", "currency": "EUR", "rate": "1.00"},
    {"rate_date": "2026-03-06", "currency": "EUR", "rate": "1.50"},
    {"rate_date": "2026-04-06", "currency": "EUR", "rate": "2.00"},
]


class TestMonthlyVolume(unittest.TestCase):
    def test_total_for_the_month(self):
        result = monthly_volume(ORDERS, FX_RATES, 2026, 3)
        self.assertEqual(result["total"], Decimal("400.00"))

    def test_lists_the_orders_behind_the_total(self):
        result = monthly_volume(ORDERS, FX_RATES, 2026, 3)
        self.assertEqual(sorted(result["order_ids"]), ["T1", "T2"])

    def test_other_months_are_excluded(self):
        result = monthly_volume(ORDERS, FX_RATES, 2026, 4)
        self.assertEqual(sorted(result["order_ids"]), ["T3"])
        self.assertEqual(result["total"], Decimal("1800.00"))


if __name__ == "__main__":
    unittest.main()
