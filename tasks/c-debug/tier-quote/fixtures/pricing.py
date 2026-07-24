"""Bulk pricing for the wholesale order tool."""


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
