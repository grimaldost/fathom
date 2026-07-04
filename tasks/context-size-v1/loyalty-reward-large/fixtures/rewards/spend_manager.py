"""Auxiliary spend manager for the rewards package."""

from .loyalty import rate_for

_REFS = (rate_for,)


def describe_spend_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "spend_manager"
