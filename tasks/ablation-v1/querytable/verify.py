"""Acceptance verifier for `querytable` (harness-side, scenario-blind).

Reads ONLY the result-view path in argv[1]. Black-box tests the candidate against a
NAIVE, obviously-correct oracle reimplemented here (list comprehensions), so grader
risk is low; the difficulty is the candidate matching the SQL null/ordering/aggregate
semantics under random inputs. `property_random` is the defect-escape catcher. Seeded.
"""

import json
import random
import sys

_ALL = (
    "where_three_valued",
    "where_neq_excludes_null",
    "order_nulls_last_asc_desc",
    "order_multikey_stable",
    "aggregate_null_semantics",
    "aggregate_avg",
    "group_none_key",
    "no_mutation",
    "property_random",
)

_OPS = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


# ---- naive oracle (obviously correct) ----
def o_where(rows, col, op, value):
    return [r for r in rows if r.get(col) is not None and _OPS[op](r.get(col), value)]


def o_order(rows, keys):
    def comp(v, desc):
        return (1, 0) if v is None else (0, -v if desc else v)

    return sorted(rows, key=lambda r: tuple(comp(r.get(c), d) for c, d in keys))


def o_agg(rows, group_by, specs):
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
            if func == "COUNT":
                row[alias] = len(vals)
            elif not vals:
                row[alias] = None
            elif func == "SUM":
                row[alias] = sum(vals)
            elif func == "AVG":
                row[alias] = sum(vals) / len(vals)
            elif func == "MIN":
                row[alias] = min(vals)
            elif func == "MAX":
                row[alias] = max(vals)
        out.append(row)
    return out


def _rows_eq(a, b):
    """List-of-dicts equality with float tolerance (for AVG)."""
    if not isinstance(a, list) or len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        if not isinstance(ra, dict) or set(ra) != set(rb):
            return False
        for k in ra:
            x, y = ra[k], rb[k]
            if isinstance(x, float) or isinstance(y, float):
                if x is None or y is None:
                    if x is not y:
                        return False
                elif abs(x - y) > 1e-9:
                    return False
            elif x != y:
                return False
    return True


def _criteria(view):
    sys.path.insert(0, view)
    R = {}
    try:
        import querytable as Q
    except Exception:
        return dict.fromkeys(_ALL, False)

    try:
        rows = [{"a": 1}, {"a": None}, {"a": 3}]
        R["where_three_valued"] = (
            Q.where(rows, "a", "=", 1) == [{"a": 1}]
            and Q.where(rows, "a", "<", 3) == [{"a": 1}]
            and Q.where(rows, "a", ">=", 1) == [{"a": 1}, {"a": 3}]
        )
    except Exception:
        R["where_three_valued"] = False

    try:
        rows = [{"a": 1}, {"a": None}, {"a": 3}]
        R["where_neq_excludes_null"] = Q.where(rows, "a", "!=", 1) == [{"a": 3}]
    except Exception:
        R["where_neq_excludes_null"] = False

    try:
        rows = [{"a": 2}, {"a": None}, {"a": 1}]
        asc = Q.order_by(rows, [("a", False)])
        desc = Q.order_by(rows, [("a", True)])
        R["order_nulls_last_asc_desc"] = asc == [{"a": 1}, {"a": 2}, {"a": None}] and desc == [
            {"a": 2},
            {"a": 1},
            {"a": None},
        ]
    except Exception:
        R["order_nulls_last_asc_desc"] = False

    try:
        rows = [
            {"a": 1, "b": 2},
            {"a": 1, "b": 1},
            {"a": 2, "b": 9},
        ]
        got = Q.order_by(rows, [("a", False), ("b", True)])
        R["order_multikey_stable"] = got == [
            {"a": 1, "b": 2},
            {"a": 1, "b": 1},
            {"a": 2, "b": 9},
        ]
    except Exception:
        R["order_multikey_stable"] = False

    try:
        rows = [{"g": 1, "v": 5}, {"g": 1, "v": None}, {"g": 2, "v": None}]
        got = Q.aggregate(rows, ["g"], [("SUM", "v", "s"), ("COUNT", "v", "c"), ("MIN", "v", "m")])
        R["aggregate_null_semantics"] = got == [
            {"g": 1, "s": 5, "c": 1, "m": 5},
            {"g": 2, "s": None, "c": 0, "m": None},
        ]
    except Exception:
        R["aggregate_null_semantics"] = False

    try:
        rows = [{"v": 2}, {"v": 4}, {"v": None}]
        got = Q.aggregate(rows, [], [("AVG", "v", "a")])
        R["aggregate_avg"] = _rows_eq(got, [{"a": 3.0}])
    except Exception:
        R["aggregate_avg"] = False

    try:
        rows = [{"g": None, "v": 1}, {"g": None, "v": 2}, {"g": 1, "v": 9}]
        got = Q.aggregate(rows, ["g"], [("SUM", "v", "s")])
        R["group_none_key"] = got == [{"g": None, "s": 3}, {"g": 1, "s": 9}]
    except Exception:
        R["group_none_key"] = False

    try:
        rows = [{"a": 1}, {"a": 2}]
        snapshot = [dict(r) for r in rows]
        Q.where(rows, "a", ">", 0)
        Q.order_by(rows, [("a", True)])
        Q.aggregate(rows, ["a"], [("COUNT", "a", "c")])
        R["no_mutation"] = rows == snapshot
    except Exception:
        R["no_mutation"] = False

    # ---- property: random tables + random op vs the naive oracle ----
    try:
        rng = random.Random(20260701)
        cols = ["a", "b", "c"]
        ok = True
        for _ in range(40):
            n = rng.randint(2, 6)
            rows = [
                {c: (None if rng.random() < 0.3 else rng.randint(0, 3)) for c in cols}
                for _ in range(n)
            ]
            kind = rng.choice(["where", "order", "aggregate"])
            if kind == "where":
                col = rng.choice(cols)
                op = rng.choice(list(_OPS))
                val = rng.randint(0, 3)
                got, exp = Q.where(rows, col, op, val), o_where(rows, col, op, val)
            elif kind == "order":
                keys = [(rng.choice(cols), rng.random() < 0.5) for _ in range(rng.randint(1, 2))]
                got, exp = Q.order_by(rows, keys), o_order(rows, keys)
            else:
                gb = [] if rng.random() < 0.4 else [rng.choice(cols)]
                func = rng.choice(["COUNT", "SUM", "MIN", "MAX"])  # AVG covered by unit test
                col = rng.choice(cols)
                specs = [(func, col, "x")]
                got, exp = Q.aggregate(rows, gb, specs), o_agg(rows, gb, specs)
            if not _rows_eq(got, exp):
                ok = False
                break
        R["property_random"] = ok
    except Exception:
        R["property_random"] = False

    return R


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    results = _criteria(sys.argv[1])
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
