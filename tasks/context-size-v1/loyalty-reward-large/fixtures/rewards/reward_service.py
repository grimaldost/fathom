"""Auxiliary reward service for the rewards package."""

from .accounts import tier_of

_REFS = (tier_of,)


def describe_reward_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "reward_service"
