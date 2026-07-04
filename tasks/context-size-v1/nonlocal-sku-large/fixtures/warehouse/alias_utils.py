"""Auxiliary alias utils for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_alias_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "alias_utils"
