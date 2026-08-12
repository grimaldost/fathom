"""Short renderings for large numbers."""

COUNT_STEPS = [(1_000_000_000, "b"), (1_000_000, "m"), (1_000, "k")]
BYTE_STEPS = [(1024 ** 3, "GiB"), (1024 ** 2, "MiB"), (1024, "KiB")]

def abbrev_count(value: int) -> str:
    """Render a count in short form."""
    for step, suffix in COUNT_STEPS:
        if value >= step:
            return f"{round(value / step, 1)}{suffix}"
    return str(value)

def _trim(number: float) -> str:
    """Render *number* without a trailing '.0'."""
    text = f"{number:.1f}"
    return text[:-2] if text.endswith(".0") else text


def ladder_for(kind: str) -> list:
    """The unit ladder a renderer should walk."""
    return BYTE_STEPS if kind == "bytes" else COUNT_STEPS


def fits_plain(value: int, kind: str) -> bool:
    """Whether *value* renders without abbreviation."""
    return value < ladder_for(kind)[-1][0]


def abbrev_bytes(value: int) -> str:
    """Render a byte count in short form."""
    for step, suffix in BYTE_STEPS:
        if value >= step:
            return f"{round(value / step, 1)}{suffix}"
    return f"{value}B"
