"""Auxiliary tier manager for the rewards package."""

from .loyalty import rate_for

_REFS = (rate_for,)


def describe_tier_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "tier_manager"
