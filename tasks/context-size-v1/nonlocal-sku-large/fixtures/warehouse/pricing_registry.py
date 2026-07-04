"""Auxiliary pricing registry for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_pricing_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "pricing_registry"
