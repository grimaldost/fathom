"""Auxiliary pricing service for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_pricing_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "pricing_service"
