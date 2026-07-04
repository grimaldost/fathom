"""Auxiliary inventory utils for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_inventory_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "inventory_utils"
