"""Per-line-item sales totals for the daily report. (ref: minimal correct add)"""

# One dict per line item; every amount is a plain float (no blanks, no messy types).
LINE_ITEMS = [
    {"sku": "A-1", "amount": 10.0},
    {"sku": "B-2", "amount": 20.5},
    {"sku": "C-3", "amount": 5.25},
    {"sku": "D-4", "amount": 100.0},
]


def grand_total(rows):
    """Sum of the amount field across the given rows."""
    return sum(row["amount"] for row in rows)
