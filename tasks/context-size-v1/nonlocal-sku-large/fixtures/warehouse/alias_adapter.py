"""Auxiliary alias adapter for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_alias_adapter() -> str:
    """Return a short tag for this auxiliary module."""
    return "alias_adapter"
