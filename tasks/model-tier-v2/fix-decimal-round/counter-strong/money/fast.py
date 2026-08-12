"""The fast backend: float arithmetic.

COUNTER-SOLUTION FOR THE STRONG ORACLE (harness-side, never staged). Decimal
quantisation, built straight from the float — `Decimal(value)`, not
`Decimal(str(value))`. Every tie the standard oracle names is binary-exact, so this
is right on all of them and the parity grid is green. On a value a float cannot hold
exactly, it quantises the float's error rather than the number the caller wrote, and
diverges from the exact backend. Only the strong oracle looks there.
"""

from decimal import ROUND_HALF_UP, Decimal


def round_half_up(value, places=0):
    """Round *value* to *places* decimal places, ties away from zero."""
    quantum = Decimal(1).scaleb(-places)
    return float(Decimal(value).quantize(quantum, rounding=ROUND_HALF_UP))
