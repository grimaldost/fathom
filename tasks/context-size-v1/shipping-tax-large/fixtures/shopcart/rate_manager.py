"""Auxiliary rate manager for the shopcart package."""

from .rates import TAX_RATE

_REFS = (TAX_RATE,)


def describe_rate_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "rate_manager"
