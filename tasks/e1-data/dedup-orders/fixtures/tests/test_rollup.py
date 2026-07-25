import unittest
from decimal import Decimal

from rollup import summarize


class TestRollup(unittest.TestCase):
    def test_unique_rows_sum_per_category(self):
        rows = [
            {"id": "1", "category": "a", "amount": "10.00"},
            {"id": "2", "category": "b", "amount": "5.00"},
            {"id": "3", "category": "a", "amount": "2.50"},
        ]
        out = summarize(rows)
        self.assertEqual(out["by_category"]["a"], Decimal("12.50"))
        self.assertEqual(out["grand_total"], Decimal("17.50"))


if __name__ == "__main__":
    unittest.main()
