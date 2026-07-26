"""pricing.registry — third-level consumer."""
from reconciler.ledgers.normalize import run as _up


def run(entries):
    return _up(entries)
