"""treasury.schema — second-level consumer."""
from reconciler.pricing.hooks import run as _up


def run(entries):
    return _up(entries)
