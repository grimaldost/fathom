"""Customer account directory (canonical source of truth)."""

_TIER = {"c_silver": "silver", "c_gold": "gold", "c_plat": "platinum"}


def tier_of(customer_id):
    """Return the loyalty tier for a customer (defaults to 'silver')."""
    return _TIER.get(customer_id, "silver")
