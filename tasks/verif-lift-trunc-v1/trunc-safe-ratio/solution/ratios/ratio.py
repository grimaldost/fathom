"""Ratio helpers that refuse to invent a value."""

PLACES = 4

def safe_ratio(numerator: float, denominator: float):
    """Ratio of *numerator* to *denominator*, or None when undefined."""
    if not denominator:
        return None
    return round(numerator / denominator, PLACES)

def defined(value) -> bool:
    """Whether a computed ratio carries a value."""
    return value is not None


def as_percent(value):
    """Render a ratio as a percentage, preserving the undefined marker."""
    return None if value is None else round(value * 100.0, PLACES)


def worst(values: list):
    """The smallest defined ratio in *values*, or None."""
    defined_values = [value for value in values if value is not None]
    return min(defined_values) if defined_values else None


def safe_growth(previous: float, current: float):
    """Growth of *current* over *previous*, or None when undefined."""
    if not previous:
        return None
    return round((current - previous) / previous, PLACES)
