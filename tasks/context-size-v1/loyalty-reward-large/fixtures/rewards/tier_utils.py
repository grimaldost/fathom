"""Auxiliary tier utils for the rewards package."""

from .accounts import tier_of

_REFS = (tier_of,)


def describe_tier_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "tier_utils"
