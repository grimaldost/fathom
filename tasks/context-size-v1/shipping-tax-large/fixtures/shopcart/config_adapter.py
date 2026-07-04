"""Auxiliary config adapter for the shopcart package."""

from .rates import TAX_RATE

_REFS = (TAX_RATE,)


def describe_config_adapter() -> str:
    """Return a short tag for this auxiliary module."""
    return "config_adapter"
