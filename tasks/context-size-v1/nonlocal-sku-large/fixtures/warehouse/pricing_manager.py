"""Auxiliary pricing manager for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_pricing_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "pricing_manager"
