import json
import unittest
from decimal import Decimal
from pathlib import Path

from daily_revenue import daily_net_revenue, load_orders

BASELINE = Path(__file__).parent / "baseline_daily_revenue.json"


def _baseline_totals():
    with BASELINE.open(encoding="utf-8") as fh:
        return {day: Decimal(value) for day, value in json.load(fh)["totals"].items()}


class TestDailyRevenue(unittest.TestCase):
    def test_matches_baseline(self):
        totals = daily_net_revenue(load_orders(Path(__file__).parent.parent / "orders.csv"))
        self.assertEqual(totals, _baseline_totals())

    def test_every_day_appears_once(self):
        rows = load_orders(Path(__file__).parent.parent / "orders.csv")
        totals = daily_net_revenue(rows)
        self.assertEqual(sorted(totals), sorted({row["day"] for row in rows}))

    def test_amounts_are_decimal(self):
        totals = daily_net_revenue(load_orders(Path(__file__).parent.parent / "orders.csv"))
        for value in totals.values():
            self.assertIsInstance(value, Decimal)


if __name__ == "__main__":
    unittest.main()
