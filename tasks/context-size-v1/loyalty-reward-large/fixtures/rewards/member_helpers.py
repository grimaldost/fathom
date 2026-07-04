"""Auxiliary member helpers for the rewards package."""

from .loyalty import rate_for

_REFS = (rate_for,)


def describe_member_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "member_helpers"
