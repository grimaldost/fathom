"""Auxiliary rate utils for the shopcart package."""

from .config import FREE_SHIPPING_OVER

_REFS = (FREE_SHIPPING_OVER,)


def describe_rate_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "rate_utils"
