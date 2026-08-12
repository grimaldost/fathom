"""Profile form validation."""

from forms import common


def validate_profile(email: str) -> bool:
    """True when *email* is valid under RULES.md."""
    return common.check_email(email)
