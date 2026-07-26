"""limits.policies — third-level consumer."""
from reconciler.custody.mapper import run as _up


def run(entries):
    return _up(entries)
