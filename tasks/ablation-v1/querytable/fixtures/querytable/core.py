"""querytable core - BASELINE (incomplete: only `=` filtering; no ordering/aggregation).

The task is to implement the full three-valued `where`, the NULLS-LAST stable
`order_by`, and the null-aware `aggregate`. See the task instruction.
"""


def where(rows, col, op, value):
    """Baseline: only equality on non-null values. INCOMPLETE for other ops / NULL."""
    if op == "=":
        return [r for r in rows if r.get(col) == value]
    return list(rows)


def order_by(rows, keys):
    """Not implemented in the baseline."""
    return list(rows)


def aggregate(rows, group_by, specs):
    """Not implemented in the baseline."""
    return []
