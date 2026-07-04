"""Auxiliary warehouse utils for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_warehouse_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "warehouse_utils"
