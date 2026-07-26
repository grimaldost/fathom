"""custody.jobs — batch helpers."""


def reconcile_batch(rows):
    return sum(rows)


def pre_reconcile(rows):
    return list(rows)
