"""Auxiliary stock utils for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_stock_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "stock_utils"
