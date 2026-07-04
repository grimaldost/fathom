"""Auxiliary inventory registry for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_inventory_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "inventory_registry"
