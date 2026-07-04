"""Auxiliary alias manager for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_alias_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "alias_manager"
