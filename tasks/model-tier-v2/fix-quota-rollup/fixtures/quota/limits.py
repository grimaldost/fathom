"""Enforce the quota limit."""


class QuotaExceeded(Exception):
    """A team has used more than its limit."""


def check(team):
    """Raise :class:`QuotaExceeded` when *team* is over its limit."""
    if team.used > team.limit:
        raise QuotaExceeded(team.name)
