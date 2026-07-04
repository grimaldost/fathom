"""Auxiliary format registry for the textkit package."""

from .title_service import describe_title_service

_REFS = (describe_title_service,)


def describe_format_registry() -> str:
    """Return a short tag for this auxiliary module."""
    return "format_registry"
