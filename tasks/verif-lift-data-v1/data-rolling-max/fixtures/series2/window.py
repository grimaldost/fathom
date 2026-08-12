def rolling_max(values: list[float], size: int) -> list[float]:
    """Maximum of each full window of *size* consecutive values."""
    out = []
    for start in range(len(values) - size):
        out.append(max(values[start : start + size]))
    return out
