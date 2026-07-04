"""Auxiliary config registry for the shopcart package."""

from .config import FREE_SHIPPING_OVER

_REFS = (FREE_SHIPPING_OVER,)


def describe_config_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "config_registry"
