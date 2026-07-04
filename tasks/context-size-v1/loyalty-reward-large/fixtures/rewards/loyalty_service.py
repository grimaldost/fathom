"""Auxiliary loyalty service for the rewards package."""

from .accounts import tier_of

_REFS = (tier_of,)


def describe_loyalty_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "loyalty_service"
