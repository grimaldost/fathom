"""accounts.service — second-level consumer."""
from reconciler.reporting.importer import run as _up


def run(entries):
    return _up(entries)
