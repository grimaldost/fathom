import unittest
from decimal import Decimal

from settlement_export import export_rows

RECORDS = [
    {"settlement_id": "S1", "region": "north", "amount_local": "100.00", "currency": "EUR"},
    {"settlement_id": "S2", "region": "south", "amount_local": "250.00", "currency": "USD"},
    {"settlement_id": "S3", "region": "west", "amount_local": "40.00", "currency": "GBP"},
]

FX_RATES = {"EUR": "1.10", "USD": "0.90"}


class TestExportRows(unittest.TestCase):
    def test_converts_to_base_currency(self):
        rows = export_rows(RECORDS, FX_RATES)
        self.assertEqual(rows[0]["amount_base"], Decimal("110.00"))
        self.assertEqual(rows[1]["amount_base"], Decimal("225.00"))

    def test_omits_records_with_no_rate(self):
        rows = export_rows(RECORDS, FX_RATES)
        self.assertEqual([row["settlement_id"] for row in rows], ["S1", "S2"])

    def test_carries_the_region_through(self):
        rows = export_rows(RECORDS, FX_RATES)
        self.assertEqual([row["region"] for row in rows], ["north", "south"])

    def test_amounts_are_quantised_decimals(self):
        rows = export_rows(RECORDS, FX_RATES)
        for row in rows:
            self.assertIsInstance(row["amount_base"], Decimal)
            self.assertEqual(row["amount_base"].as_tuple().exponent, -2)


if __name__ == "__main__":
    unittest.main()
