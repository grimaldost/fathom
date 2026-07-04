"""Auxiliary shipping helpers for the shopcart package."""

from .rates import TAX_RATE

_REFS = (TAX_RATE,)


def describe_shipping_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "shipping_helpers"
