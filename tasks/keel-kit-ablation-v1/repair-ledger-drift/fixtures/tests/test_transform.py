import unittest

from tinyetl.transform import (
    TransformError,
    dedupe_orders,
    normalize_currency,
    to_record,
)


class NormalizeCurrencyTests(unittest.TestCase):
    def test_accepts_supported_code(self):
        self.assertEqual(normalize_currency("EUR"), "EUR")

    def test_rejects_unknown_code(self):
        with self.assertRaises(TransformError):
            normalize_currency("XYZ")


class DedupeOrdersTests(unittest.TestCase):
    def test_keeps_first_occurrence(self):
        rows = [
            {"order_id": "a", "region": "north"},
            {"order_id": "a", "region": "south"},
            {"order_id": "b", "region": "east"},
        ]
        self.assertEqual([r["region"] for r in dedupe_orders(rows)], ["north", "east"])

    def test_rejects_row_without_order_id(self):
        with self.assertRaises(TransformError):
            dedupe_orders([{"region": "north"}])


class ToRecordTests(unittest.TestCase):
    def test_amount_becomes_cents(self):
        row = {"order_id": "a", "region": "north", "amount": "12.34", "currency": "EUR"}
        self.assertEqual(to_record(row)["amount_cents"], 1234)


if __name__ == "__main__":
    unittest.main()
