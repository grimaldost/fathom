def first_index(ordered: list[int], target: int, *, strict: bool = False) -> int:
    """Index of the first occurrence of *target*, or -1."""
    low, high = 0, len(ordered) - 1
    found = -1
    while low <= high:
        mid = (low + high) // 2
        if ordered[mid] == target:
            found = mid
            high = mid - 1
        elif ordered[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return found
