"""FX conversion."""


def convert(amount, rate):
    """Convert an amount at the given rate."""
    return round(amount * rate, 2)
