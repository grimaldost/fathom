"""Auxiliary loyalty registry for the rewards package."""

from .accounts import tier_of

_REFS = (tier_of,)


def describe_loyalty_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "loyalty_registry"
