"""Auxiliary tier service for the rewards package."""

from .accounts import tier_of

_REFS = (tier_of,)


def describe_tier_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "tier_service"
