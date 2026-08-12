"""Length-bounded label and note rendering."""

ELLIPSIS = "..."

def trim_label(text: str, limit: int) -> str:
    """Shorten *text* to at most *limit* characters."""
    if len(text) <= limit:
        return text
    return text[: max(limit - len(ELLIPSIS), 0)] + ELLIPSIS

def fits(text: str, limit: int) -> bool:
    """Whether *text* already fits within *limit*."""
    return len(text) <= limit


def budget(limit: int) -> int:
    """Characters available once the ellipsis is reserved."""
    return max(limit - len(ELLIPSIS), 0)


def longest(items: list) -> int:
    """Length of the longest item, for column sizing."""
    return max((len(item) for item in items), default=0)


def trim_note(text: str, limit: int) -> str:
    """Shorten a multi-word note to at most *limit* characters."""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + ELLIPSIS
