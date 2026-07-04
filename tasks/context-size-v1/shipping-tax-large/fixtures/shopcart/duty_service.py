"""Auxiliary duty service for the shopcart package."""

from .config import FREE_SHIPPING_OVER

_REFS = (FREE_SHIPPING_OVER,)


def describe_duty_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "duty_service"
