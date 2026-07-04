"""Auxiliary bonus service for the rewards package."""

from .accounts import tier_of

_REFS = (tier_of,)


def describe_bonus_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "bonus_service"
