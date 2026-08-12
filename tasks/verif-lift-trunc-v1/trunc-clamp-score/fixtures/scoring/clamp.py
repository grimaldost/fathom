"""Bounded score and weight coercion."""

SCORE_LOW = 0.0
SCORE_HIGH = 100.0
WEIGHT_LOW = 0.0
WEIGHT_HIGH = 1.0

def clamp_score(value: float) -> float:
    """Coerce *value* into the score range."""
    if value < SCORE_LOW:
        return SCORE_LOW
    return value

def score_band(value: float) -> str:
    """The reporting band a clamped score falls in."""
    if value >= 80.0:
        return "high"
    if value >= 40.0:
        return "mid"
    return "low"


def normalise(value: float, low: float, high: float) -> float:
    """Position of *value* within [low, high] as a 0..1 fraction."""
    span = high - low
    return 0.0 if span == 0 else (value - low) / span


def describe(value: float) -> str:
    """One-line description of a clamped score."""
    return f"{value:.1f} ({score_band(value)})"


def clamp_weight(value: float) -> float:
    """Coerce *value* into the weight range."""
    if value < WEIGHT_LOW:
        return WEIGHT_LOW
    return value
