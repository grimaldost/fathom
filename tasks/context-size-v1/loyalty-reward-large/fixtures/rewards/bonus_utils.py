"""Auxiliary bonus utils for the rewards package."""

from .accounts import tier_of

_REFS = (tier_of,)


def describe_bonus_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "bonus_utils"
