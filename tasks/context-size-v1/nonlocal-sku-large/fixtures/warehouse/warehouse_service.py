"""Auxiliary warehouse service for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_warehouse_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "warehouse_service"
