"""Helpers shared by every form module."""


def normalise_domain(domain: str) -> str:
    """Lower-case a domain and strip a single trailing dot."""
    return domain.lower().rstrip(".")
