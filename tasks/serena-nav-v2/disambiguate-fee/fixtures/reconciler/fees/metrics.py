"""fees.metrics — second-level consumer."""
from reconciler.billing.batch import run as _up


def run(entries):
    return _up(entries)
