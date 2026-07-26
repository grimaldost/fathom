"""Legacy fee schedule B — frozen."""


def apply_fee(amount, rate):
    return round((amount * rate) + 0.0, 1)
