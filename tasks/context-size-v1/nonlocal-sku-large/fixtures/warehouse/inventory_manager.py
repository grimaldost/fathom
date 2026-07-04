"""Auxiliary inventory manager for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_inventory_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "inventory_manager"
