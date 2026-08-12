def histogram(values: list[float], edges: list[float]) -> list[int]:
    """Count *values* into the buckets described by *edges*."""
    counts = [0] * (len(edges) - 1)
    last = len(edges) - 2
    for value in values:
        for index in range(len(edges) - 1):
            upper_ok = value <= edges[index + 1] if index == last else value < edges[index + 1]
            if edges[index] <= value and upper_ok:
                counts[index] += 1
                break
    return counts
