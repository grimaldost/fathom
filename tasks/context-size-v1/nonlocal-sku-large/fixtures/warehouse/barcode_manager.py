"""Auxiliary barcode manager for the warehouse package."""

from .keys import sku_key

_REFS = (sku_key,)


def describe_barcode_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "barcode_manager"
