"""Auxiliary inventory helpers for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_inventory_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "inventory_helpers"
