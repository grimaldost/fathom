"""Profile form validation."""

from forms.common import normalise_domain


def validate_profile(email: str) -> bool:
    """True when *email* may be stored on a profile."""
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local or local.startswith("."):
        return False
    if ".." in local:
        return False
    domain = normalise_domain(domain)
    if "." not in domain:
        return False
    return True
