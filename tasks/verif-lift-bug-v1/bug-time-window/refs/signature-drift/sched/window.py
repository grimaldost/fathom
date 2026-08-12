def slots(start: int, end: int, step: int, *, strict: bool = False) -> list[int]:
    """Slot start minutes covering the half-open window [start, end)."""
    out = []
    current = start
    while current + step <= end:
        out.append(current)
        current += step
    return out
