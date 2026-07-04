"""Auxiliary member registry for the rewards package."""

from .accounts import tier_of

_REFS = (tier_of,)


def describe_member_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "member_registry"
