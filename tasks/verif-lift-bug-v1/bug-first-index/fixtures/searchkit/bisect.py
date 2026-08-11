def first_index(ordered: list[int], target: int) -> int:
    """Index of the first occurrence of *target*, or -1."""
    low, high = 0, len(ordered) - 1
    while low <= high:
        mid = (low + high) // 2
        if ordered[mid] == target:
            return mid
        if ordered[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
