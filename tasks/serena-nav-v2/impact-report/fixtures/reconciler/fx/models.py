"""fx.models — second-level consumer."""
from reconciler.clearing.cache import run as _up


def run(entries):
    return _up(entries)
