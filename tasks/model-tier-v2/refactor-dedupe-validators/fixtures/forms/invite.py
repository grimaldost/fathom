"""Invite form validation."""

from forms.common import normalise_domain


def validate_invite(email: str) -> bool:
    """True when *email* may be sent an invitation."""
    email = email.lower()
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local:
        return False
    domain = normalise_domain(domain)
    if "." not in domain:
        return False
    return True
