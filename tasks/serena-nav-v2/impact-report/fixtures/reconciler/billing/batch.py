"""billing.batch — reconciliation consumer (shape 1)."""
from reconciler.core.engine import reconcile as _rc


def run(entries):
    return _rc(entries)
