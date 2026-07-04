"""Auxiliary bonus helpers for the rewards package."""

from .loyalty import rate_for

_REFS = (rate_for,)


def describe_bonus_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "bonus_helpers"
