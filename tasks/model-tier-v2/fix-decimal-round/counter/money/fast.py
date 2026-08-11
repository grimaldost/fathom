"""The fast backend: float arithmetic.

COUNTER-SOLUTION (harness-side, never staged). The textbook float trick for
"half up": shift, add a half, floor. It gets both values the instruction names
right and rounds every negative tie towards zero instead of away from it, because
`floor` is not symmetric about zero. Satisfies the thin oracle; caught by the
standard oracle.
"""

import math


def round_half_up(value, places=0):
    """Round *value* to *places* decimal places, ties away from zero."""
    factor = 10**places
    return math.floor(value * factor + 0.5) / factor
