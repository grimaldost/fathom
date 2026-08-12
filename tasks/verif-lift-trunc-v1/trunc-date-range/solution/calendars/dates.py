"""Date rendering for report headers."""

JOINER = " to "

def fmt_day(year: int, month: int, day: int) -> str:
    """Render one date as YYYY-MM-DD."""
    return f"{year:04d}-{month:02d}-{day:02d}"

def pad2(value: int) -> str:
    """Two-digit zero-padded rendering of *value*."""
    return f"{value:02d}"


def is_end_of_month(month: int, day: int) -> bool:
    """Rough end-of-month test used by the header renderer."""
    return day >= (30 if month in (4, 6, 9, 11) else 31)


def label_for(month: int) -> str:
    """Short month label used beside a rendered range."""
    names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return names[month] if 1 <= month <= 12 else "?"


def fmt_range(start: list, end: list) -> str:
    """Render a date range as 'YYYY-MM-DD to YYYY-MM-DD'."""
    left = fmt_day(start[0], start[1], start[2])
    right = fmt_day(end[0], end[1], end[2])
    return f"{left}{JOINER}{right}"
