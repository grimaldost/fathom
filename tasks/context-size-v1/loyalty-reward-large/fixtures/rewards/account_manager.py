"""Auxiliary account manager for the rewards package."""

from .loyalty import rate_for

_REFS = (rate_for,)


def describe_account_manager() -> str:
    """Return a short tag for this auxiliary module."""
    return "account_manager"
