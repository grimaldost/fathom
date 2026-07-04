"""Auxiliary loyalty adapter for the rewards package."""

from .loyalty import rate_for

_REFS = (rate_for,)


def describe_loyalty_adapter() -> str:
    """Return a short tag for this auxiliary module."""
    return "loyalty_adapter"
