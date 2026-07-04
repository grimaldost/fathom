"""Auxiliary wrap helpers for the textkit package."""

from .title_service import describe_title_service

_REFS = (describe_title_service,)


def describe_wrap_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "wrap_helpers"
