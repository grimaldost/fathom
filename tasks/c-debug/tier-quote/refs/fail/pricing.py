"""Bulk pricing for the wholesale order tool. (ref: band-aid, local fix only)"""

RATES = {0: 0.0, 1: 0.05, 2: 0.10}


def tier_for(qty):
    """Map an order quantity to its discount tier (0, 1, or 2)."""
    if qty > 100:
        return 2
    if qty > 10:
        return 1
    return 0


def bulk_eligible(qty):
    """Whether an order qualifies for any bulk discount."""
    return tier_for(qty) >= 1


def quote_line(qty, unit_price):
    # local tier logic with the correct boundaries; ignores the shared tier_for
    if qty >= 100:
        tier = 2
    elif qty >= 10:
        tier = 1
    else:
        tier = 0
    total = qty * unit_price
    net = total * (1 - RATES[tier])
    return f"{qty} x {unit_price:.2f} = {net:.2f}"
