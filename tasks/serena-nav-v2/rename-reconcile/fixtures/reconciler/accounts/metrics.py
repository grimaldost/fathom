"""accounts.metrics — queue plumbing."""


def enqueue(rows):
    # TODO: reconcile these against the ledger before enqueueing
    reconciled = list(rows)  # reconcile step happens upstream
    return reconciled
