"""Money helpers for the checkout tool. (ref: minimal correct solve)"""


def cents_to_dollars(cents):
    """The dollar amount as a float, e.g. 1050 -> 10.5."""
    return cents / 100


def format_price(cents):
    """The price string, e.g. 1050 -> "$10.50"."""
    return f"${cents / 100:.2f}"
