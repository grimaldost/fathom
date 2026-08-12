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


def category_as_of(lookup, product_id, order_date):
    """The lookup row in force for *product_id* on *order_date*.

    `product_lookup` is grained on (product_id, effective_from), so a join on
    product_id alone fans out. The row in force is the latest one whose
    `effective_from` is on or before the order date (contract: Grain).
    """
    best = None
    for entry in lookup:
        if entry["product_id"] != product_id:
            continue
        if entry["effective_from"] > order_date:
            continue
        if best is None or entry["effective_from"] > best["effective_from"]:
            best = entry
    return best["category"] if best is not None else None


def revenue_by_category(orders, lookup):
    """Total revenue per product category, one category per order."""
    totals = {}
    for order in orders:
        category = category_as_of(lookup, order["product_id"], order["order_date"])
        if category is None:
            continue
        totals[category] = totals.get(category, Decimal("0.00")) + Decimal(order["amount"])
    return totals


def main():
    orders = load_csv("orders.csv")
    lookup = load_csv("product_lookup.csv")
    for category, revenue in sorted(revenue_by_category(orders, lookup).items()):
        print(f"{category}\t{revenue}")


if __name__ == "__main__":
    main()
