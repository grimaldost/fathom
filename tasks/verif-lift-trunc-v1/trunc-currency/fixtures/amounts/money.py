"""Minor-unit amount rendering."""

MINOR_PER_MAJOR = 100
SEPARATOR = ","

def fmt_amount(minor: int) -> str:
    """Render *minor* units as a major-unit amount."""
    return f"{minor / MINOR_PER_MAJOR:.2f}"

def to_major(minor: int) -> float:
    """Major units for *minor*."""
    return minor / MINOR_PER_MAJOR


def group_digits(text: str) -> str:
    """Insert SEPARATOR every three digits of an integer part."""
    whole, _, fraction = text.partition(".")
    grouped = f"{int(whole):,}".replace(",", SEPARATOR)
    return f"{grouped}.{fraction}" if fraction else grouped


def is_negative(minor: int) -> bool:
    """Whether an amount renders with a leading minus."""
    return minor < 0


def fmt_total(minors: list) -> str:
    """Render the total of *minors* as a major-unit amount."""
    return f"{sum(minors) / MINOR_PER_MAJOR:.2f}"
