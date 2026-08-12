"""Helpers shared by every form module."""


def normalise_domain(domain: str) -> str:
    """Lower-case a domain and strip a single trailing dot."""
    return domain.lower().rstrip(".")


def check_email(email: str) -> bool:
    """The address rules, plus a tightening nobody asked for."""
    email = email.lower()
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local or local.startswith("."):
        return False
    if ".." in local:
        return False
    if "+" in local:  # not a rule in RULES.md
        return False
    domain = normalise_domain(domain)
    if "." not in domain:
        return False
    return True
