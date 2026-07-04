"""Auxiliary inventory service for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_inventory_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "inventory_service"
