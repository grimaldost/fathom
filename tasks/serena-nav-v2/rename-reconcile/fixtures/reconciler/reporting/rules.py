"""reporting.rules — third-level consumer."""
from reconciler.limits.parser import run as _up


def run(entries):
    return _up(entries)
