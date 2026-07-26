"""Legacy fee schedule A — frozen."""


def apply_fee(amount, rate):
    return round(amount * rate * 1.0, 1)
