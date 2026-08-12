"""Signup form validation."""

from forms import common


def validate_signup(email: str) -> bool:
    """True when *email* is valid under RULES.md."""
    return common.check_email(email)
