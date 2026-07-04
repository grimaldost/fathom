"""Auxiliary pricing utils for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_pricing_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "pricing_utils"
