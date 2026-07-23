"""Attach each order's region from the customer table and total revenue by region."""

import csv
import json
from decimal import Decimal
from pathlib import Path


def revenue_by_region(orders, customers):
    """Return a mapping of region name to total order revenue.

    Each order has a "customer_id" and an "amount"; each customer row maps a
    "customer_id" to its "region". Orders are matched to their region and the
    amounts summed per region.
    """
    joined = []
    for order in orders:
        for customer in customers:
            if customer["customer_id"] == order["customer_id"]:
                joined.append({**order, "region": customer["region"]})

    totals = {}
    for row in joined:
        region = row["region"]
        totals[region] = totals.get(region, Decimal("0")) + Decimal(row["amount"])
    return totals


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    here = Path(__file__).resolve().parent
    orders = load_rows(here / "orders.csv")
    customers = load_rows(here / "customers.csv")
    totals = revenue_by_region(orders, customers)
    payload = {region: str(total) for region, total in totals.items()}
    (here / "revenue.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
