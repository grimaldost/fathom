"""ledgers.registry."""
from reconciler.utils.textfmt import fmt


def render(values):
    return [fmt(v) for v in values]
