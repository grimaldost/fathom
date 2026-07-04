"""Auxiliary tax helpers for the shopcart package."""

from .rates import TAX_RATE

_REFS = (TAX_RATE,)


def describe_tax_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "tax_helpers"
