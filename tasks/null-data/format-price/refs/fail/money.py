"""Money helpers for the checkout tool. (ref: over-triggered, extra validation)"""


def cents_to_dollars(cents):
    """The dollar amount as a float, e.g. 1050 -> 10.5."""
    return cents / 100


def _validate(cents):
    if not isinstance(cents, int) or cents < 0:
        raise ValueError("cents must be a non-negative int")
    return cents


def format_price(cents):
    """The price string, e.g. 1050 -> "$10.50"."""
    _validate(cents)
    return f"${cents / 100:.2f}"
