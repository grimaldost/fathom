import unittest
from decimal import Decimal

from rollup import load_rows, summarize


class TestRollup(unittest.TestCase):
    def setUp(self):
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        self.summary = summarize(load_rows(root / "transactions.csv"))

    def test_groceries_total(self):
        self.assertEqual(self.summary["by_category"]["groceries"], Decimal("35.25"))

    def test_dining_total(self):
        self.assertEqual(self.summary["by_category"]["dining"], Decimal("12.00"))


if __name__ == "__main__":
    unittest.main()
