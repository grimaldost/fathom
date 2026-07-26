"""accounts.loader — reconciliation consumer (shape 4)."""
import reconciler.core.engine as eng


def run(entries):
    return eng.reconcile(entries)
