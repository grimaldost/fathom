"""Record usage as it happens.

COUNTER-SOLUTION FOR THE STRONG ORACLE, part 1 of 3 (harness-side, never staged).
A `team_total` helper is added here so every reader can get the true number, and
`record` is left as it was so its behaviour does not change for existing callers.
The rollup field itself is never refreshed.
"""


def record(member, amount):
    """Charge *amount* to *member*. A negative amount is a refund."""
    member.used += amount


def team_total(team):
    """The team's usage, computed from its members."""
    return sum(member.used for member in team.members)
