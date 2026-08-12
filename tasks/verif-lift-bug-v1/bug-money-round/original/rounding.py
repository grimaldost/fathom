def round_half_even(amount: float, places: int) -> float:
    """Round *amount* to *places* decimals, half to even."""
    scale = 10 ** places
    scaled = amount * scale
    whole = int(scaled)
    fraction = scaled - whole
    if fraction >= 0.5:
        whole += 1
    return whole / scale
