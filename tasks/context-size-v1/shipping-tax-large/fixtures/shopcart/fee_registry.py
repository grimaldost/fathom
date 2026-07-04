"""Auxiliary fee registry for the shopcart package."""

from .config import FREE_SHIPPING_OVER

_REFS = (FREE_SHIPPING_OVER,)


def describe_fee_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "fee_registry"
