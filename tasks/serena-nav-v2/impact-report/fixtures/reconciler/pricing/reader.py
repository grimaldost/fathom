"""pricing.reader — second-level consumer."""
from reconciler.limits.export import run as _up


def run(entries):
    return _up(entries)
