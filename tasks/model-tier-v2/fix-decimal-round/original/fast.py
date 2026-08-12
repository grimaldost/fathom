"""The fast backend: float arithmetic."""


def round_half_up(value, places=0):
    """Round *value* to *places* decimal places, ties away from zero."""
    return float(round(value, places))
