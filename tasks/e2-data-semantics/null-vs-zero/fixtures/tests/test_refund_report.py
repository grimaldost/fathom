import unittest
from decimal import Decimal

from refund_report import build_report

REGIONS = ["north", "south"]

REFUNDS = [
    {"refund_id": "R1", "region": "north", "amount": "80.00"},
    {"refund_id": "R2", "region": "north", "amount": "40.00"},
    {"refund_id": "R3", "region": "south", "amount": "45.00"},
]


class TestBuildReport(unittest.TestCase):
    def test_one_row_per_region_in_order(self):
        report = build_report(REGIONS, REFUNDS)
        self.assertEqual([row["region"] for row in report], REGIONS)

    def test_nets_the_refund_rows(self):
        report = build_report(REGIONS, REFUNDS)
        self.assertEqual(report[0]["refund_total"], Decimal("120.00"))
        self.assertEqual(report[1]["refund_total"], Decimal("45.00"))

    def test_counts_the_refund_rows(self):
        report = build_report(REGIONS, REFUNDS)
        self.assertEqual(report[0]["refund_count"], 2)
        self.assertEqual(report[1]["refund_count"], 1)

    def test_totals_are_decimal(self):
        report = build_report(REGIONS, REFUNDS)
        for row in report:
            self.assertIsInstance(row["refund_total"], Decimal)


if __name__ == "__main__":
    unittest.main()
