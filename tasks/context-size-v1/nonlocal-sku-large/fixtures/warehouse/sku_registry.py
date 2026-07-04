"""Auxiliary sku registry for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_sku_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "sku_registry"
