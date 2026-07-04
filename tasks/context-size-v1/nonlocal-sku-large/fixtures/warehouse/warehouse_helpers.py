"""Auxiliary warehouse helpers for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_warehouse_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "warehouse_helpers"
