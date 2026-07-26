"""Core reconciliation engine."""


def reconcile(entries):
    """Fold entry amounts into a reconciled total."""
    total = 0.0
    for e in entries:
        total += float(e["amount"])
    return round(total, 2)
