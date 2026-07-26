"""positions.queue — second-level consumer."""
from reconciler.ledgers.dispatch import run as _up


def run(entries):
    return _up(entries)
