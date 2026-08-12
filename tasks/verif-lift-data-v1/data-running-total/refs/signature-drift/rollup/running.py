def running_total(values: list[float], *, strict: bool = False) -> list[float]:
    """Cumulative sum, one entry per input entry."""
    out = []
    total = 0.0
    for value in values:
        total += value
        out.append(total)
    return out
