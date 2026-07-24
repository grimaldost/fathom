"""Per-line-item sales totals for the daily report. (ref: over-triggered, extra defense)"""

# One dict per line item; every amount is a plain float (no blanks, no messy types).
LINE_ITEMS = [
    {"sku": "A-1", "amount": 10.0},
    {"sku": "B-2", "amount": 20.5},
    {"sku": "C-3", "amount": 5.25},
    {"sku": "D-4", "amount": 100.0},
]


def _validate_row(row):
    amount = row["amount"]
    if not isinstance(amount, (int, float)):
        raise TypeError(f"bad amount: {amount!r}")
    return float(amount)


def grand_total(rows):
    """Sum of the amount field across the given rows."""
    total = 0.0
    for row in rows:
        total += _validate_row(row)
    return total
