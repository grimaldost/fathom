"""Auxiliary config helpers for the shopcart package."""

from .rates import TAX_RATE

_REFS = (TAX_RATE,)


def describe_config_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "config_helpers"
