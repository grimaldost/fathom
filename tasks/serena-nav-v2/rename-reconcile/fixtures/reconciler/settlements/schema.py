"""settlements.schema — third-level consumer."""
from reconciler.payments.policies import run as _up


def run(entries):
    return _up(entries)
