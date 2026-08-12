"""Record usage as it happens."""


def record(member, amount):
    """Charge *amount* to *member*. A negative amount is a refund."""
    if member.team is not None:
        member.team.add_usage(member, amount)
    else:
        member.used += amount
