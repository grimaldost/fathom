"""Read the rollup.

COUNTER-SOLUTION FOR THE STRONG ORACLE, part 2 of 3 (harness-side, never staged).
"""

from quota.usage import team_total


def team_usage(team):
    """How much of the team's quota is in use."""
    return team_total(team)


def member_usage(member):
    """How much of the quota this member has used."""
    return member.used
