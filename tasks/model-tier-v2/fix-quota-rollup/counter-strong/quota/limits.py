"""Enforce the quota limit.

COUNTER-SOLUTION FOR THE STRONG ORACLE, part 3 of 3 (harness-side, never staged).
Both remaining-quota readers now compute the total instead of reading the rollup,
so every criterion the standard oracle names is green while `team.used` stays
stale. Only a check that reads the invariant at its source sees the difference.
"""

from quota.usage import team_total


class QuotaExceeded(Exception):
    """A team has used more than its limit."""


def check(team):
    """Raise :class:`QuotaExceeded` when *team* is over its limit."""
    if team_total(team) > team.limit:
        raise QuotaExceeded(team.name)
