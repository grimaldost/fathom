"""custody.cleanup — reconciliation consumer (shape 3)."""
from reconciler import reconcile


def run(entries):
    return reconcile(entries)
