"""Teams, members, and the usage rollup.

COUNTER-SOLUTION FOR THE STRONG ORACLE (harness-side, never staged). `remaining`
now computes the total the same way the other readers do; the `used` field it was
built around is still only refreshed by `add_usage` and `add_member`.
"""

from quota.usage import team_total


class Member:
    """One person's usage against their team's quota."""

    def __init__(self, name):
        self.name = name
        self.used = 0
        self.team = None


class Team:
    """A team with a quota limit and a rolled-up usage total."""

    def __init__(self, name, limit):
        self.name = name
        self.limit = limit
        self.members = []
        self.used = 0

    def add_member(self, member):
        """Attach *member* to this team and refresh the rollup."""
        member.team = self
        self.members.append(member)
        self.recompute()

    def add_usage(self, member, amount):
        """Charge *amount* to *member*, keeping the rollup in step."""
        member.used += amount
        self.recompute()

    def recompute(self):
        """Rebuild the rollup from the members."""
        self.used = sum(member.used for member in self.members)

    def remaining(self):
        """How much of the quota is left."""
        return self.limit - team_total(self)
