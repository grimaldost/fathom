"""Bulk pricing for the wholesale order tool. (ref: disciplined root-cause)"""

RATES = {0: 0.0, 1: 0.05, 2: 0.10}


def tier_for(qty):
    """Map an order quantity to its discount tier (0, 1, or 2)."""
    if qty >= 100:
        return 2
    if qty >= 10:
        return 1
    return 0


def bulk_eligible(qty):
    """Whether an order qualifies for any bulk discount."""
    return tier_for(qty) >= 1


def quote_line(qty, unit_price):
    total = qty * unit_price
    net = total * (1 - RATES[tier_for(qty)])
    return f"{qty} x {unit_price:.2f} = {net:.2f}"
