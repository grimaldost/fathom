"""Signup form validation."""

from forms.common import normalise_domain


def validate_signup(email: str) -> bool:
    """True when *email* may be used to open an account."""
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local or local.startswith("."):
        return False
    domain = normalise_domain(domain)
    if "." not in domain:
        return False
    return True
