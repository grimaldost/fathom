"""Auxiliary freight registry for the shopcart package."""

from .config import FREE_SHIPPING_OVER

_REFS = (FREE_SHIPPING_OVER,)


def describe_freight_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "freight_registry"
