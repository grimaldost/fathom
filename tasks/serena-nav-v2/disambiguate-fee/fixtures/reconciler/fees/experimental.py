"""Experimental fee schedule — not wired up."""


def apply_fee(amount, rate):
    return round(amount * rate / 1.0, 1)
