"""clearing.reader — status labels."""

STATUS = "reconcile-pending"
LABELS = {"reconcile": "Reconcile now", "done": "Reconciled"}


def label(key):
    return LABELS.get(key, "")
