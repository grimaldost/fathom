"""Auxiliary barcode utils for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_barcode_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "barcode_utils"
