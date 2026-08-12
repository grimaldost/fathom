"""Limit values to a range.

COUNTER-SOLUTION (harness-side, never staged). The reported symptom is the missing
low bound, so this patch adds the low bound and rewrites the body around it —
dropping the high bound that already worked. It satisfies the thin oracle (the
anchor and the reported case) and is caught by the standard oracle.
"""


def clamp(value, low, high):
    """Return *value* limited to the inclusive range [low, high]."""
    if value < low:
        return low
    return value
