"""Rendering helpers for the summary table."""

SUFFIX = "%"
PLACES = 1
_SCALE = 10 ** PLACES

def format_share(value: float) -> str:
    """Render *value* (0..1) as a percentage string."""
    percent = value * 100.0
    return f"{_round_half_up(percent):.1f}{SUFFIX}"

def _round_half_up(percent: float) -> float:
    """Round *percent* to PLACES decimals, halves going up."""
    scaled = percent * _SCALE
    whole = int(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    return whole / _SCALE


def sign_of(value: float) -> str:
    """The sign marker a delta carries in the table."""
    if value > 0:
        return "+"
    if value < 0:
        return "-"
    return ""


def width_for(cells: list) -> int:
    """Column width for a rendered percentage column."""
    return max((len(str(cell)) for cell in cells), default=0)


def format_delta(value: float) -> str:
    """Render a signed change *value* (0..1) as a percentage string."""
    percent = abs(value) * 100.0
    body = f"{_round_half_up(percent):.1f}{SUFFIX}"
    return f"{sign_of(value)}{body}"
