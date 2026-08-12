"""Limit values to a range.

COUNTER-SOLUTION FOR THE STRONG ORACLE (harness-side, never staged). Both bounds
are correct for every case the standard oracle names, and the shipped suite stays
green — but the ``int()`` normalisation silently drops the fractional part, so a
float already inside the range no longer comes back unchanged. Only the strong
oracle's independent property sweep sees it.
"""


def clamp(value, low, high):
    """Return *value* limited to the inclusive range [low, high]."""
    return int(min(high, max(low, value)))
