"""Auxiliary reward registry for the rewards package."""

from .accounts import tier_of

_REFS = (tier_of,)


def describe_reward_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "reward_registry"
