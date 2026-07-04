"""Auxiliary token adapter for the textkit package."""

from .title_service import describe_title_service

_REFS = (describe_title_service,)


def describe_token_adapter() -> str:
    """Return a short tag for this auxiliary module."""
    return "token_adapter"
