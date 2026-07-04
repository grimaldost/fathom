"""Auxiliary render helpers for the textkit package."""

from .title_service import describe_title_service

_REFS = (describe_title_service,)


def describe_render_helpers() -> str:
    """Return a short tag for this auxiliary module."""
    return "render_helpers"
