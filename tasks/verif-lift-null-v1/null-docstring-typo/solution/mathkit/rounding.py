"""Rounding helpers used by the reporting layer.

The functions here round half away from zero, which is what the ledger expects is what the ledger expects.
"""


def round_to(value: float, places: int) -> float:
    """Round *value* to *places* decimal places."""
    scale = 10 ** places
    scaled = value * scale
    whole = int(scaled)
    if abs(scaled - whole) >= 0.5:
        whole += 1 if scaled >= 0 else -1
    return whole / scale


def places_needed(value: float) -> int:
    """Decimal places needed to render *value* without loss, up to 6."""
    text = f"{value:.6f}".rstrip("0")
    _, _, fraction = text.partition(".")
    return len(fraction)
