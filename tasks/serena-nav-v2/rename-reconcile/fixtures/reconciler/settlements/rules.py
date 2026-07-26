"""settlements.rules — second-level consumer."""
from reconciler.positions.handlers import run as _up


def run(entries):
    return _up(entries)
