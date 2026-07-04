"""Auxiliary sku manager for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_sku_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "sku_manager"
