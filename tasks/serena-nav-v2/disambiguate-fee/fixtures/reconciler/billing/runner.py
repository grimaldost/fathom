"""Billing runner."""
from reconciler.fees.standard import apply_fee


def charge(amount, rate):
    return apply_fee(amount, rate)
