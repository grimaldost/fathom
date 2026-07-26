"""payments.queue — third-level consumer."""
from reconciler.fees.metrics import run as _up


def run(entries):
    return _up(entries)
