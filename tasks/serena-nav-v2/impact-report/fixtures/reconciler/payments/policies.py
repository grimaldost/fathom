"""payments.policies — second-level consumer."""
from reconciler.fx.config import run as _up


def run(entries):
    return _up(entries)
