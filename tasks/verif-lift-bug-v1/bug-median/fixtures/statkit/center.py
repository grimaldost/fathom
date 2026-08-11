def median(values: list[float]) -> float:
    """The median of *values*."""
    ordered = sorted(values)
    return float(ordered[len(ordered) // 2])
