"""limits.parser — second-level consumer."""
from reconciler.fees.client import run as _up


def run(entries):
    return _up(entries)
