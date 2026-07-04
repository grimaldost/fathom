"""Auxiliary title utils for the textkit package."""

from .title_service import describe_title_service

_REFS = (describe_title_service,)


def describe_title_utils() -> str:
    """Return a short tag for this auxiliary module."""
    return "title_utils"
