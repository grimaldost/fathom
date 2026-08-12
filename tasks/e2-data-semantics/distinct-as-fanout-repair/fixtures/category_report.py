"""Category revenue report.

Public API:
    load_csv(path) -> list[dict]
    revenue_by_category(orders, lookup) -> dict[str, Decimal]
"""

import csv
from decimal import Decimal
from pathlib import Path


def load_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def revenue_by_category(orders, lookup):
    """Total revenue per product category."""
    totals = {}
    for order in orders:
        for entry in lookup:
            if entry["product_id"] != order["product_id"]:
                continue
            category = entry["category"]
            totals[category] = totals.get(category, Decimal("0.00")) + Decimal(order["amount"])
    return totals


def main():
    orders = load_csv("orders.csv")
    lookup = load_csv("product_lookup.csv")
    for category, revenue in sorted(revenue_by_category(orders, lookup).items()):
        print(f"{category}\t{revenue}")


if __name__ == "__main__":
    main()
