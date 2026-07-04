"""Auxiliary config service for the shopcart package."""

from .config import FREE_SHIPPING_OVER

_REFS = (FREE_SHIPPING_OVER,)


def describe_config_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "config_service"
