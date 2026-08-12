"""The exact backend: decimal arithmetic."""

from decimal import ROUND_HALF_UP, Decimal


def round_half_up(value, places=0):
    """Round *value* to *places* decimal places, ties away from zero."""
    quantum = Decimal(1).scaleb(-places)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))
