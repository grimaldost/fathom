"""Limit values to a range."""


def clamp(value, low, high):
    """Return *value* limited to the inclusive range [low, high]."""
    if value > high:
        return high
    return value
