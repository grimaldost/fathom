"""Sort key construction for the rendered listing."""

FALLBACK = "\uffff"

def sort_key_name(value: str) -> str:
    """Sort key for a name column."""
    return value.strip().casefold() or FALLBACK

def normalise(value: str) -> str:
    """The comparable spelling of a cell value."""
    return value.strip().casefold()


def missing_last(key: str) -> str:
    """Push an empty key to the end of the listing."""
    return key or FALLBACK


def compare(left: str, right: str) -> int:
    """Three-way comparison of two prepared sort keys."""
    if left == right:
        return 0
    return -1 if left < right else 1


def sort_key_group(value: str) -> str:
    """Sort key for a group column."""
    return missing_last(normalise(value))
