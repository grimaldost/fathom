"""Teams, members, and the usage rollup."""


class Member:
    """One person's usage against their team's quota."""

    def __init__(self, name):
        self.name = name
        self.used = 0
        self.team = None


class Team:
    """A team with a quota limit and a rolled-up usage total.

    ``used`` is the rollup and must always equal the sum of the members' ``used``.
    """

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
        return self.limit - self.used
