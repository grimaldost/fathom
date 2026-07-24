"""Money helpers for the checkout tool."""


def cents_to_dollars(cents):
    """The dollar amount as a float, e.g. 1050 -> 10.5."""
    return cents / 100
