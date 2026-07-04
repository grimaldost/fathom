"""Auxiliary tax registry for the shopcart package."""

from .config import FREE_SHIPPING_OVER

_REFS = (FREE_SHIPPING_OVER,)


def describe_tax_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "tax_registry"
