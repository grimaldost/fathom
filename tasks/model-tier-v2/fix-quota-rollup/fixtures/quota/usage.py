"""Record usage as it happens."""


def record(member, amount):
    """Charge *amount* to *member*. A negative amount is a refund."""
    member.used += amount
