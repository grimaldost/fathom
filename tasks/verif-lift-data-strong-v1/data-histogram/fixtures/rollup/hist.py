def histogram(values: list[float], edges: list[float]) -> list[int]:
    """Count *values* into the buckets described by *edges*."""
    counts = [0] * (len(edges) - 1)
    for value in values:
        for index in range(len(edges) - 1):
            if edges[index] <= value < edges[index + 1]:
                counts[index] += 1
                break
    return counts
