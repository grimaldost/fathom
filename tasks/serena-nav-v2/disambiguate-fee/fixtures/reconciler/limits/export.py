"""limits.export — reconciliation consumer (shape 2)."""
from reconciler.core import engine


def run(entries):
    return engine.reconcile(entries)
