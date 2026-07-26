"""positions.reader — third-level consumer."""
from reconciler.fx.models import run as _up


def run(entries):
    return _up(entries)
