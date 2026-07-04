"""querytable core - REFERENCE SOLUTION (full three-valued query engine).

Used only by the bank-validation gate; never staged into an agent workspace.
"""

_OPS = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def where(rows, col, op, value):
    cmp = _OPS[op]
    out = []
    for r in rows:
        v = r.get(col)
        if v is None:  # SQL 3-valued: NULL comparison is UNKNOWN -> excluded
            continue
        if cmp(v, value):
            out.append(r)
    return out


def _key_component(v, descending):
    if v is None:
        return (1, 0)  # NULLS LAST in both directions (1 sorts after 0)
    return (0, -v if descending else v)


def order_by(rows, keys):
    return sorted(rows, key=lambda r: tuple(_key_component(r.get(c), d) for c, d in keys))


def _agg(func, vals):
    if func == "COUNT":
        return len(vals)
    if not vals:
        return None  # SUM/AVG/MIN/MAX over no non-null values -> None (SQL)
    if func == "SUM":
        return sum(vals)
    if func == "AVG":
        return sum(vals) / len(vals)
    if func == "MIN":
        return min(vals)
    if func == "MAX":
        return max(vals)
    raise ValueError(f"unknown aggregate {func}")


def aggregate(rows, group_by, specs):
    groups: dict = {}
    order: list = []
    for r in rows:
        key = tuple(r.get(g) for g in group_by)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(r)
    out = []
    for key in order:
        grp = groups[key]
        row = {g: key[i] for i, g in enumerate(group_by)}
        for func, col, alias in specs:
            vals = [r.get(col) for r in grp if r.get(col) is not None]
            row[alias] = _agg(func, vals)
        out.append(row)
    return out
