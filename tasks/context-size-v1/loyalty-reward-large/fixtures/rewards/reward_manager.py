"""Auxiliary reward manager for the rewards package."""

from .loyalty import rate_for

_REFS = (rate_for,)


def describe_reward_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "reward_manager"
