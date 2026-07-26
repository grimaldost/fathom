"""fx.config — reconciliation consumer (shape 0)."""
from reconciler.core.engine import reconcile


def run(entries):
    return reconcile(entries)
