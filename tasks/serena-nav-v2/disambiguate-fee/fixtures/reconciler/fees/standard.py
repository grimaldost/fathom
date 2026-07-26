"""Standard fee schedule (the one the daily pipeline uses)."""


def apply_fee(amount, rate):
    """Fee on an amount. NOTE: rounds to 1 decimal."""
    return round(amount * rate, 1)
