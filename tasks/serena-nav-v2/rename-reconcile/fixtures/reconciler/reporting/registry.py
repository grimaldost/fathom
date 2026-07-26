"""reporting.registry — second-level consumer."""
from reconciler.payments.filters import run as _up


def run(entries):
    return _up(entries)
