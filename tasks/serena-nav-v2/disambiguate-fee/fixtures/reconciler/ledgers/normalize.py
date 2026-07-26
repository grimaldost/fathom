"""ledgers.normalize — second-level consumer."""
from reconciler.custody.cleanup import run as _up


def run(entries):
    return _up(entries)
