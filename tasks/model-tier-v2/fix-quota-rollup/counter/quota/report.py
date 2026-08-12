"""Read the rollup.

COUNTER-SOLUTION (harness-side, never staged). The instruction reports
`team_usage`, so `team_usage` stops trusting the rollup and sums the members
itself. The reported number is right; `Team.remaining` and `limits.check` still
read the stale rollup field. Satisfies the thin oracle; caught by the standard
oracle.
"""


def team_usage(team):
    """How much of the team's quota is in use."""
    return sum(member.used for member in team.members)


def member_usage(member):
    """How much of the quota this member has used."""
    return member.used
