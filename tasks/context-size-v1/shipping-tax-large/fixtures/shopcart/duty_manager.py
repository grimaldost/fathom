"""Auxiliary duty manager for the shopcart package."""

from .rates import TAX_RATE

_REFS = (TAX_RATE,)


def describe_duty_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "duty_manager"
