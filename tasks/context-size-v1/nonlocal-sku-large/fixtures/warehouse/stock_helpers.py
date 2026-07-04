"""Auxiliary stock helpers for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_stock_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "stock_helpers"
