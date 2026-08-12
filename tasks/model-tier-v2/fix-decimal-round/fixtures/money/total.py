"""Order-line totals, through either backend."""

from money import exact, fast

BACKENDS = {"fast": fast, "exact": exact}


def line_total(quantity, unit_price, backend="fast"):
    """The rounded total for *quantity* units at *unit_price*, to two places."""
    return BACKENDS[backend].round_half_up(quantity * unit_price, 2)
