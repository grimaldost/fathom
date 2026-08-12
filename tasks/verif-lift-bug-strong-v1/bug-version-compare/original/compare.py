def compare_versions(a: str, b: str) -> int:
    """Compare dotted numeric versions; -1, 0 or 1."""
    left = a.split(".")
    right = b.split(".")
    for x, y in zip(left, right):
        if x != y:
            return -1 if x < y else 1
    if len(left) == len(right):
        return 0
    return -1 if len(left) < len(right) else 1
