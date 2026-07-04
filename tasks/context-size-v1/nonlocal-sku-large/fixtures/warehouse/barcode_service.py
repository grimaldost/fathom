"""Auxiliary barcode service for the warehouse package."""

from .aliases import canonical

_REFS = (canonical,)


def describe_barcode_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "barcode_service"
