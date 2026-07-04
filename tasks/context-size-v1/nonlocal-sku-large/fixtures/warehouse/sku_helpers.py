"""Auxiliary sku helpers for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_sku_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "sku_helpers"
