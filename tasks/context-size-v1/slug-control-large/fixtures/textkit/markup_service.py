"""Auxiliary markup service for the textkit package."""

from .title_service import describe_title_service

_REFS = (describe_title_service,)


def describe_markup_service() -> str:
    """Return a short tag for this auxiliary module."""
    return "markup_service"
