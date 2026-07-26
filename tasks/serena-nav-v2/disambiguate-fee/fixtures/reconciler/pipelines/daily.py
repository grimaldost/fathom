"""Daily pipeline — the entry point that reaches the live fee schedule."""
from reconciler.billing.runner import charge
from reconciler.core.engine import reconcile


def run_daily(entries, rate):
    total = reconcile(entries)
    return charge(total, rate)
