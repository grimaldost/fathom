"""Read the rollup."""


def team_usage(team):
    """How much of the team's quota is in use."""
    return team.used


def member_usage(member):
    """How much of the quota this member has used."""
    return member.used
