"""Core settlement arithmetic."""


def settle(entries):
    """Sum entry amounts into a settlement total."""
    total = 0.0
    for e in entries:
        total += float(e["amount"])
    return round(total, 2)


def settle_batch(batches):
    """Settlement per batch."""
    return [settle(b) for b in batches]


def accrue(principal, rate, days):
    """Simple accrual on an ACT/360 basis."""
    return round(principal * rate * days / 360.0, 2)
