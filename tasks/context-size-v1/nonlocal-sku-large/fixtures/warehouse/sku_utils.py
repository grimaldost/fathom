"""Auxiliary sku utils for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_sku_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "sku_utils"
