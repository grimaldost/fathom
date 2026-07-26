"""custody.mapper — second-level consumer."""
from reconciler.accounts.api import run as _up


def run(entries):
    return _up(entries)
