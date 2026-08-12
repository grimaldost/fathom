def merge_spans(spans: list[list[int]]) -> list[list[int]]:
    """Merge overlapping or touching half-open spans."""
    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
