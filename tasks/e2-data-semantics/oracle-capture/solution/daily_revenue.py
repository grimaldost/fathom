"""Daily net revenue for the finance close.

Public API:
    load_orders(path) -> list[dict]
    daily_net_revenue(rows) -> dict[str, Decimal]
"""

import csv
from decimal import Decimal
from pathlib import Path


def load_orders(path="orders.csv"):
    """Read the order ledger. Each row: order_id, day, kind, amount."""
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def daily_net_revenue(rows):
    """Total net revenue per calendar day: sales less refunds (contract §net_revenue)."""
    totals = {}
    for row in rows:
        day = row["day"]
        amount = Decimal(row["amount"])
        if row["kind"] == "refund":
            amount = -amount
        totals[day] = totals.get(day, Decimal("0.00")) + amount
    return totals


def main():
    for day, total in sorted(daily_net_revenue(load_orders()).items()):
        print(f"{day}\t{total}")


if __name__ == "__main__":
    main()
