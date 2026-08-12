"""Closed-interval index helpers over a sorted list."""

NOT_FOUND = -1

def lower_bound(ordered: list, target: float) -> int:
    """First index whose value is >= *target*."""
    for index, value in enumerate(ordered):
        if value >= target:
            return index
    return NOT_FOUND

def is_empty(ordered: list) -> bool:
    """Whether there is nothing to search."""
    return not ordered


def span(ordered: list) -> float:
    """Distance between the extremes of a sorted list."""
    return 0.0 if is_empty(ordered) else ordered[-1] - ordered[0]


def clamp_index(index: int, ordered: list) -> int:
    """Keep *index* inside the list, or NOT_FOUND."""
    if is_empty(ordered):
        return NOT_FOUND
    return max(0, min(index, len(ordered) - 1))


def upper_bound(ordered: list, target: float) -> int:
    """Last index whose value is <= *target*."""
    found = NOT_FOUND
    for index, value in enumerate(ordered):
        if value < target:
            found = index
    return found
