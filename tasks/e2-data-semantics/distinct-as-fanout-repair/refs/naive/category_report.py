"""Category revenue report.

NAIVE REFERENCE -- the fix a first pass reaches for: the totals were too high
because the join duplicated orders, so count each order once. The row count and
the grand total come back to the ledger's own numbers, and the shipped suite
stays green -- but which category an order lands in is now whichever lookup row
happened to be read first.

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
    """Total revenue per product category, counting each order exactly once."""
    totals = {}
    counted = set()
    for order in orders:
        for entry in lookup:
            if entry["product_id"] != order["product_id"]:
                continue
            if order["order_id"] in counted:
                continue
            counted.add(order["order_id"])
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
