"""DATA class: an aggregate/reshape defect that is NAMED in the instruction, plus a
second case with the same root cause that is NOT named.

``spec_met`` scores the named defect and is expected to saturate -- it is the
covariate.  ``output_correct_on_subtle_case`` scores the unnamed case and is the
co-primary with real headroom: a fix aimed only at the sentence in the instruction
gets it wrong.  ``regression_check_present`` is the common footprint criterion,
scored the same way as in the BUG class.

The shipped baseline suite covers only cases both the buggy and the fixed source get
right, so it cannot manufacture a red after the inverse edit.
"""

from __future__ import annotations

DATA = [
    dict(
        id="data-group-total",
        package="rollup",
        module="group",
        func="total_by",
        contract=(
            "`total_by(rows, key, field)` sums `field` per distinct `key` value and\n"
            "returns `{key_value: total}`. Every key present in `rows` appears in the\n"
            "result, including keys whose rows all sum to zero. A `None` in `field` counts\n"
            "as zero; a row that LACKS `field` entirely is a data error and raises\n"
            "`KeyError`."
        ),
        buggy='''def total_by(rows: list[dict], key: str, field: str) -> dict:
    """Sum *field* per distinct *key* value."""
    totals: dict = {}
    for row in rows:
        value = row.get(field) or 0
        if not value:
            continue
        totals[row[key]] = totals.get(row[key], 0) + value
    return totals
''',
        fixed='''def total_by(rows: list[dict], key: str, field: str) -> dict:
    """Sum *field* per distinct *key* value."""
    totals: dict = {}
    for row in rows:
        if field not in row:
            raise KeyError(field)
        value = row[field] or 0
        totals[row[key]] = totals.get(row[key], 0) + value
    return totals
''',
        base_cases=[
            [
                [[{"r": "a", "n": 2}, {"r": "a", "n": 3}, {"r": "b", "n": 4}], "r", "n"],
                {"a": 5, "b": 4},
            ]
        ],
        edge_cases=[
            [[[{"r": "a", "n": 0}], "r", "n"], {"a": 0}],
            [[[{"r": "a", "n": 3}, {"r": "b", "n": 0}], "r", "n"], {"a": 3, "b": 0}],
        ],
        subtle_cases=[
            [[[{"r": "a", "m": 1}], "r", "n"], {"raises": "KeyError"}],
            [[[{"r": "a", "n": 2}, {"r": "b"}], "r", "n"], {"raises": "KeyError"}],
        ],
        instruction=(
            "`rollup.group.total_by` skips every row whose `field` is zero, so a key whose\n"
            "rows are all zero vanishes from the result entirely and a consumer cannot tell\n"
            "it apart from a key that had no rows. Keep zero-valued rows in the sums, per\n"
            "the package README."
        ),
    ),
    dict(
        id="data-daily-rate",
        package="rollup",
        module="rate",
        func="daily_rate",
        contract=(
            "`daily_rate(rows)` returns `{day: events/actors}` rounded to 3 decimals.\n"
            "A day with zero actors has an undefined rate and is reported as `None`, never\n"
            "dropped and never zero."
        ),
        buggy='''def daily_rate(rows: list[dict]) -> dict:
    """Events per actor for each day."""
    out: dict = {}
    for row in rows:
        out[row["day"]] = round(row["events"] / max(row["actors"], 1), 3)
    return out
''',
        fixed='''def daily_rate(rows: list[dict]) -> dict:
    """Events per actor for each day."""
    out: dict = {}
    for row in rows:
        actors = row["actors"]
        out[row["day"]] = None if actors == 0 else round(row["events"] / actors, 3)
    return out
''',
        base_cases=[[[[{"day": "d1", "events": 10, "actors": 4}]], {"d1": 2.5}]],
        edge_cases=[
            [[[{"day": "d1", "events": 0, "actors": 0}]], {"d1": None}],
            [[[{"day": "d1", "events": 7, "actors": 0}]], {"d1": None}],
        ],
        subtle_cases=[
            [
                [
                    [
                        {"day": "d1", "events": 3, "actors": 0},
                        {"day": "d2", "events": 6, "actors": 3},
                    ]
                ],
                {"d1": None, "d2": 2.0},
            ]
        ],
        instruction=(
            "`rollup.rate.daily_rate` clamps the denominator to 1, so a day with zero actors\n"
            "reports a rate equal to its event count instead of the undefined marker the\n"
            "README specifies. Report an undefined rate as `None`."
        ),
    ),
    dict(
        id="data-topk",
        package="rollup",
        module="topk",
        func="top_k",
        contract=(
            "`top_k(rows, k)` returns the `k` rows with the largest `score`, highest first.\n"
            "Ties break by `name` ascending, so the output is stable for equal scores."
        ),
        buggy='''def top_k(rows: list[dict], k: int) -> list[dict]:
    """The *k* highest-scoring rows, highest first."""
    ordered = sorted(rows, key=lambda row: row["score"], reverse=True)
    return ordered[:k]
''',
        fixed='''def top_k(rows: list[dict], k: int) -> list[dict]:
    """The *k* highest-scoring rows, highest first."""
    ordered = sorted(rows, key=lambda row: (-row["score"], row["name"]))
    return ordered[:k]
''',
        base_cases=[
            [
                [[{"name": "a", "score": 3}, {"name": "b", "score": 9}], 1],
                [{"name": "b", "score": 9}],
            ]
        ],
        edge_cases=[
            [
                [[{"name": "z", "score": 5}, {"name": "a", "score": 5}], 2],
                [{"name": "a", "score": 5}, {"name": "z", "score": 5}],
            ]
        ],
        subtle_cases=[
            [
                [
                    [
                        {"name": "m", "score": 4},
                        {"name": "b", "score": 7},
                        {"name": "a", "score": 4},
                    ],
                    3,
                ],
                [{"name": "b", "score": 7}, {"name": "a", "score": 4}, {"name": "m", "score": 4}],
            ]
        ],
        instruction=(
            "`rollup.topk.top_k` leaves rows with equal scores in whatever order they\n"
            "arrived, so the output is not stable. Break ties by `name` ascending as the\n"
            "README states; the ordering by score is already right."
        ),
    ),
    dict(
        id="data-left-join",
        package="joinkit",
        module="left",
        func="left_join",
        contract=(
            "`left_join(left, right, key)` keeps every left row. A left row with no match\n"
            "gets `None` for the right fields; a left row matching several right rows\n"
            "produces one output row per match. Where a right field collides with a field\n"
            "the left row already carries, the LEFT value wins -- a join never silently\n"
            "overwrites the driving side."
        ),
        buggy='''def left_join(left: list[dict], right: list[dict], key: str) -> list[dict]:
    """Left join *left* onto *right* on *key*."""
    index = {row[key]: row for row in right}
    out = []
    for row in left:
        match = index.get(row[key])
        merged = dict(row)
        merged["tag"] = match["tag"] if match else None
        out.append(merged)
    return out
''',
        fixed='''def left_join(left: list[dict], right: list[dict], key: str) -> list[dict]:
    """Left join *left* onto *right* on *key*."""
    index: dict = {}
    for row in right:
        index.setdefault(row[key], []).append(row)
    out = []
    for row in left:
        matches = index.get(row[key], [])
        if not matches:
            merged = dict(row)
            merged.setdefault("tag", None)
            out.append(merged)
            continue
        for match in matches:
            merged = dict(row)
            if "tag" not in merged:
                merged["tag"] = match["tag"]
            out.append(merged)
    return out
''',
        base_cases=[
            [
                [[{"id": 1}], [{"id": 1, "tag": "x"}], "id"],
                [{"id": 1, "tag": "x"}],
            ]
        ],
        edge_cases=[
            [
                [[{"id": 1}], [{"id": 1, "tag": "x"}, {"id": 1, "tag": "y"}], "id"],
                [{"id": 1, "tag": "x"}, {"id": 1, "tag": "y"}],
            ]
        ],
        subtle_cases=[
            [
                [[{"id": 1, "tag": "L"}], [{"id": 1, "tag": "x"}], "id"],
                [{"id": 1, "tag": "L"}],
            ],
            [
                [[{"id": 1, "tag": "L"}], [{"id": 1, "tag": "x"}, {"id": 1, "tag": "y"}], "id"],
                [{"id": 1, "tag": "L"}, {"id": 1, "tag": "L"}],
            ],
        ],
        instruction=(
            "`joinkit.left.left_join` keeps only the LAST right-hand row for a key, because\n"
            "it builds a one-row-per-key index, so a left row matching several right rows\n"
            "produces one output row instead of several. Fan the matches out as the README\n"
            "describes; the unmatched-left-row behaviour is already right."
        ),
    ),
    dict(
        id="data-latest-per-key",
        package="dedupe",
        module="latest",
        func="latest_per_key",
        contract=(
            "`latest_per_key(rows, key)` keeps the row with the greatest `ts` per key.\n"
            "When two rows share the greatest `ts`, the one appearing LAST in the input\n"
            "wins, so the result is defined for ties."
        ),
        buggy='''def latest_per_key(rows: list[dict], key: str) -> list[dict]:
    """Keep the greatest-*ts* row per *key*."""
    best: dict = {}
    for row in rows:
        current = best.get(row[key])
        if current is None or row["ts"] > current["ts"]:
            best[row[key]] = row
    return [best[k] for k in best]
''',
        fixed='''def latest_per_key(rows: list[dict], key: str) -> list[dict]:
    """Keep the greatest-*ts* row per *key*."""
    best: dict = {}
    for row in rows:
        current = best.get(row[key])
        if current is None or row["ts"] >= current["ts"]:
            best[row[key]] = row
    return [best[k] for k in best]
''',
        base_cases=[
            [
                [[{"k": "a", "ts": 1, "v": "old"}, {"k": "a", "ts": 2, "v": "new"}], "k"],
                [{"k": "a", "ts": 2, "v": "new"}],
            ]
        ],
        edge_cases=[
            [
                [[{"k": "a", "ts": 5, "v": "first"}, {"k": "a", "ts": 5, "v": "second"}], "k"],
                [{"k": "a", "ts": 5, "v": "second"}],
            ]
        ],
        subtle_cases=[
            [
                [
                    [
                        {"k": "a", "ts": 3, "v": "x"},
                        {"k": "b", "ts": 3, "v": "y"},
                        {"k": "b", "ts": 3, "v": "z"},
                    ],
                    "k",
                ],
                [{"k": "a", "ts": 3, "v": "x"}, {"k": "b", "ts": 3, "v": "z"}],
            ]
        ],
        instruction=(
            "`dedupe.latest.latest_per_key` keeps the FIRST row when two rows share the\n"
            "greatest `ts`, but the README says the last one in input order wins. Make ties\n"
            "resolve the documented way; the strictly-greater case already behaves."
        ),
    ),
    dict(
        id="data-running-total",
        package="rollup",
        module="running",
        func="running_total",
        contract=(
            "`running_total(values)` returns the cumulative sum, one entry per input entry,\n"
            "starting with the first value itself. Negative values reduce the running sum."
        ),
        buggy='''def running_total(values: list[float]) -> list[float]:
    """Cumulative sum, one entry per input entry."""
    out = []
    total = 0.0
    for value in values:
        total += abs(value)
        out.append(total)
    return out
''',
        fixed='''def running_total(values: list[float]) -> list[float]:
    """Cumulative sum, one entry per input entry."""
    out = []
    total = 0.0
    for value in values:
        total += value
        out.append(total)
    return out
''',
        base_cases=[[[[1, 2, 3]], [1.0, 3.0, 6.0]], [[[]], []]],
        edge_cases=[[[[5, -2]], [5.0, 3.0]], [[[-1, -1]], [-1.0, -2.0]]],
        subtle_cases=[[[[3, -3, 4]], [3.0, 0.0, 4.0]], [[[0, -5, 5]], [0.0, -5.0, 0.0]]],
        instruction=(
            "`rollup.running.running_total` adds the absolute value of each entry, so a\n"
            "negative entry increases the running sum instead of reducing it. Accumulate the\n"
            "signed values as the README describes."
        ),
    ),
    dict(
        id="data-histogram",
        package="rollup",
        module="hist",
        func="histogram",
        contract=(
            "`histogram(values, edges)` counts values into half-open buckets `[lo, hi)`,\n"
            "except the LAST bucket which is closed `[lo, hi]` so the maximum edge is\n"
            "counted. Values outside the edges are not counted."
        ),
        buggy='''def histogram(values: list[float], edges: list[float]) -> list[int]:
    """Count *values* into the buckets described by *edges*."""
    counts = [0] * (len(edges) - 1)
    for value in values:
        for index in range(len(edges) - 1):
            if edges[index] <= value < edges[index + 1]:
                counts[index] += 1
                break
    return counts
''',
        fixed='''def histogram(values: list[float], edges: list[float]) -> list[int]:
    """Count *values* into the buckets described by *edges*."""
    counts = [0] * (len(edges) - 1)
    last = len(edges) - 2
    for value in values:
        for index in range(len(edges) - 1):
            upper_ok = value <= edges[index + 1] if index == last else value < edges[index + 1]
            if edges[index] <= value and upper_ok:
                counts[index] += 1
                break
    return counts
''',
        base_cases=[[[[1, 2, 5], [0, 3, 6]], [2, 1]], [[[], [0, 1]], [0]]],
        edge_cases=[[[[6], [0, 3, 6]], [0, 1]], [[[10], [0, 5, 10]], [0, 1]]],
        subtle_cases=[[[[5], [0, 5]], [1]], [[[5, 6], [0, 5]], [1]]],
        instruction=(
            "`rollup.hist.histogram` drops a value that sits exactly on the highest edge,\n"
            "because every bucket is half-open. The README closes the LAST bucket so the\n"
            "maximum is counted. Fix the counting; values outside the edges stay uncounted."
        ),
    ),
    dict(
        id="data-pct-share",
        package="rollup",
        module="share",
        func="pct_share",
        contract=(
            "`pct_share(rows)` returns `{name: percent}` rounded to 2 decimals, where the\n"
            "percentages are each row's `value` over the total. When the total is zero every\n"
            "share is `0.0` -- never a division error and never a dropped key. A row whose\n"
            "`value` is `None` counts as zero."
        ),
        buggy='''def pct_share(rows: list[dict]) -> dict:
    """Each row's percentage share of the total."""
    total = sum(row["value"] for row in rows)
    return {row["name"]: round(row["value"], 2) for row in rows} if not total else {
        row["name"]: round(100.0 * row["value"] / total, 2) for row in rows
    }
''',
        fixed='''def pct_share(rows: list[dict]) -> dict:
    """Each row's percentage share of the total."""
    values = {row["name"]: row["value"] or 0 for row in rows}
    total = sum(values.values())
    if not total:
        return dict.fromkeys(values, 0.0)
    return {name: round(100.0 * value / total, 2) for name, value in values.items()}
''',
        base_cases=[
            [[[{"name": "a", "value": 1}, {"name": "b", "value": 3}]], {"a": 25.0, "b": 75.0}]
        ],
        edge_cases=[
            [[[{"name": "a", "value": 5}, {"name": "b", "value": -5}]], {"a": 0.0, "b": 0.0}],
            [[[{"name": "a", "value": 2}, {"name": "b", "value": -2}]], {"a": 0.0, "b": 0.0}],
        ],
        subtle_cases=[
            [[[{"name": "a", "value": None}, {"name": "b", "value": 3}]], {"a": 0.0, "b": 100.0}],
            [[[{"name": "a", "value": None}]], {"a": 0.0}],
        ],
        instruction=(
            "`rollup.share.pct_share` returns the raw values instead of shares when the total\n"
            "is zero, so a group whose values cancel out reports whatever numbers it happened\n"
            "to hold as if they were percentages. Return `0.0` for every key in that case,\n"
            "per the README."
        ),
    ),
    dict(
        id="data-forward-fill",
        package="series2",
        module="fill",
        func="forward_fill",
        contract=(
            "`forward_fill(values)` replaces each `None` with the most recent non-`None`\n"
            "value before it. Leading `None`s have nothing to carry forward and stay `None`."
        ),
        buggy='''def forward_fill(values: list) -> list:
    """Carry the last non-None value forward over each None."""
    out = []
    last = 0
    for value in values:
        if value is None:
            out.append(last)
        else:
            last = value
            out.append(value)
    return out
''',
        fixed='''def forward_fill(values: list) -> list:
    """Carry the last non-None value forward over each None."""
    out = []
    last = None
    for value in values:
        if value is None:
            out.append(last)
        else:
            last = value
            out.append(value)
    return out
''',
        base_cases=[[[[1, None, 2]], [1, 1, 2]], [[[4, 5]], [4, 5]]],
        edge_cases=[[[[None, 3]], [None, 3]], [[[None, None, 7]], [None, None, 7]]],
        subtle_cases=[[[[None]], [None]], [[[None, None]], [None, None]]],
        instruction=(
            "`series2.fill.forward_fill` substitutes `0` for a leading `None` because it\n"
            "seeds the carry value with zero. The README says a leading `None` stays `None`.\n"
            "Fix the seed; the ordinary carry-forward already behaves."
        ),
    ),
    dict(
        id="data-weekly-buckets",
        package="series2",
        module="resample",
        func="to_weekly",
        contract=(
            "`to_weekly(rows, weeks)` returns one entry per week in `weeks`, in that order,\n"
            "summing the `amount` of the rows in each week. A week with no rows reports 0,\n"
            "so the series has no gaps."
        ),
        buggy='''def to_weekly(rows: list[dict], weeks: list[str]) -> list[dict]:
    """One summed entry per week in *weeks*."""
    totals: dict = {}
    for row in rows:
        totals[row["week"]] = totals.get(row["week"], 0) + row["amount"]
    return [{"week": week, "amount": totals[week]} for week in weeks if week in totals]
''',
        fixed='''def to_weekly(rows: list[dict], weeks: list[str]) -> list[dict]:
    """One summed entry per week in *weeks*."""
    totals: dict = {}
    for row in rows:
        totals[row["week"]] = totals.get(row["week"], 0) + row["amount"]
    return [{"week": week, "amount": totals.get(week, 0)} for week in weeks]
''',
        base_cases=[
            [
                [[{"week": "w1", "amount": 2}, {"week": "w2", "amount": 3}], ["w1", "w2"]],
                [{"week": "w1", "amount": 2}, {"week": "w2", "amount": 3}],
            ]
        ],
        edge_cases=[
            [
                [[{"week": "w1", "amount": 2}], ["w1", "w2"]],
                [{"week": "w1", "amount": 2}, {"week": "w2", "amount": 0}],
            ]
        ],
        subtle_cases=[
            [[[], ["w1", "w2"]], [{"week": "w1", "amount": 0}, {"week": "w2", "amount": 0}]],
            [
                [[{"week": "w3", "amount": 5}], ["w1", "w2", "w3"]],
                [
                    {"week": "w1", "amount": 0},
                    {"week": "w2", "amount": 0},
                    {"week": "w3", "amount": 5},
                ],
            ],
        ],
        instruction=(
            "`series2.resample.to_weekly` omits a week that has no rows, so the returned\n"
            "series has holes and is shorter than `weeks`. Emit one entry per requested\n"
            "week, with 0 for the empty ones, as the README describes."
        ),
    ),
    dict(
        id="data-sum-amounts",
        package="moneykit",
        module="totals",
        func="sum_amounts",
        contract=(
            "`sum_amounts(rows)` sums minor units (integers) and returns\n"
            '`{"currency": c, "minor": n}`. Rows of mixed currency cannot be summed and\n'
            "raise `ValueError`. An empty input raises `ValueError` too -- there is no\n"
            "currency to report."
        ),
        buggy='''def sum_amounts(rows: list[dict]) -> dict:
    """Sum minor units across rows of one currency."""
    total = 0
    currency = ""
    for row in rows:
        total += row["minor"]
        currency = row["currency"]
    return {"currency": currency, "minor": total}
''',
        fixed='''def sum_amounts(rows: list[dict]) -> dict:
    """Sum minor units across rows of one currency."""
    if not rows:
        raise ValueError("no rows to sum")
    currencies = {row["currency"] for row in rows}
    if len(currencies) > 1:
        raise ValueError(f"mixed currencies: {sorted(currencies)}")
    return {"currency": rows[0]["currency"], "minor": sum(row["minor"] for row in rows)}
''',
        base_cases=[
            [
                [[{"currency": "AAA", "minor": 100}, {"currency": "AAA", "minor": 250}]],
                {"currency": "AAA", "minor": 350},
            ]
        ],
        edge_cases=[
            [
                [[{"currency": "AAA", "minor": 100}, {"currency": "BBB", "minor": 250}]],
                {"raises": "ValueError"},
            ]
        ],
        subtle_cases=[[[[]], {"raises": "ValueError"}]],
        instruction=(
            "`moneykit.totals.sum_amounts` adds minor units across currencies and labels the\n"
            "result with whichever currency happened to come last, silently producing a\n"
            "meaningless total. Raise `ValueError` on mixed currencies, per the README."
        ),
    ),
    dict(
        id="data-median-by",
        package="rollup",
        module="medgroup",
        func="median_by",
        contract=(
            "`median_by(rows, key)` returns `{key_value: median}`. For an even-sized group\n"
            "the median is the mean of the two middle values; a single-element group has\n"
            "that element as its median. A row whose `value` is `None` is missing data and\n"
            "is left out of its group's median; a group of nothing but `None` has median\n"
            "`None`."
        ),
        buggy='''def median_by(rows: list[dict], key: str) -> dict:
    """Median *value* per *key* group."""
    groups: dict = {}
    for row in rows:
        groups.setdefault(row[key], []).append(row["value"])
    out: dict = {}
    for name, values in groups.items():
        values.sort()
        middle = len(values) // 2
        out[name] = (values[middle - 1] + values[middle]) / 2
    return out
''',
        fixed='''def median_by(rows: list[dict], key: str) -> dict:
    """Median *value* per *key* group."""
    groups: dict = {}
    for row in rows:
        bucket = groups.setdefault(row[key], [])
        if row["value"] is not None:
            bucket.append(row["value"])
    out: dict = {}
    for name, values in groups.items():
        if not values:
            out[name] = None
            continue
        values.sort()
        middle = len(values) // 2
        if len(values) % 2 == 1:
            out[name] = float(values[middle])
        else:
            out[name] = (values[middle - 1] + values[middle]) / 2
    return out
''',
        base_cases=[
            [[[{"g": "a", "value": 1}, {"g": "a", "value": 3}], "g"], {"a": 2.0}],
        ],
        edge_cases=[
            [
                [[{"g": "a", "value": 1}, {"g": "a", "value": 2}, {"g": "a", "value": 9}], "g"],
                {"a": 2.0},
            ]
        ],
        subtle_cases=[
            [
                [[{"g": "a", "value": 1}, {"g": "a", "value": None}, {"g": "a", "value": 3}], "g"],
                {"a": 2.0},
            ],
            [[[{"g": "a", "value": None}], "g"], {"a": None}],
        ],
        instruction=(
            "`rollup.medgroup.median_by` always averages two middle values, so an odd-sized\n"
            "group gets the mean of the wrong pair. Return the true middle value for odd\n"
            "sizes, per the README; even sizes already behave."
        ),
    ),
    dict(
        id="data-null-rate",
        package="quality",
        module="nulls",
        func="null_rate",
        contract=(
            "`null_rate(rows, field)` returns the share of rows whose `field` is missing,\n"
            "`None`, or an empty/whitespace-only string, rounded to 3 decimals. With no\n"
            "rows the rate is undefined and reported as `None`."
        ),
        buggy='''def null_rate(rows: list[dict], field: str) -> float:
    """Share of rows whose *field* is null-ish."""
    nulls = sum(1 for row in rows if row.get(field) is None)
    return round(nulls / len(rows), 3) if rows else 0.0
''',
        fixed='''def null_rate(rows: list[dict], field: str):
    """Share of rows whose *field* is null-ish."""
    if not rows:
        return None
    nulls = 0
    for row in rows:
        value = row.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            nulls += 1
    return round(nulls / len(rows), 3)
''',
        base_cases=[
            [[[{"a": 1}, {"a": None}], "a"], 0.5],
            [[[{"a": 1}, {"a": 2}], "a"], 0.0],
        ],
        edge_cases=[
            [[[{"a": ""}, {"a": 2}], "a"], 0.5],
            [[[{"a": "   "}, {"a": None}], "a"], 1.0],
        ],
        subtle_cases=[[[[], "a"], None]],
        instruction=(
            "`quality.nulls.null_rate` counts only `None` as null, so an empty or\n"
            "whitespace-only string is reported as populated and the rate understates the\n"
            "problem. Count the null-ish values the README lists."
        ),
    ),
    dict(
        id="data-pivot-counts",
        package="reshape",
        module="pivot",
        func="pivot_counts",
        contract=(
            "`pivot_counts(rows, rows_key, cols_key, columns)` returns one dict per distinct\n"
            "row key, carrying a count for EVERY column in `columns` -- zero where there are\n"
            "no rows. Several rows sharing a (row, column) pair accumulate."
        ),
        buggy='''def pivot_counts(rows: list[dict], rows_key: str, cols_key: str, columns: list[str]) -> list[dict]:
    """Count rows into a row-key by column-key grid."""
    grid: dict = {}
    for row in rows:
        cell = grid.setdefault(row[rows_key], {})
        cell[row[cols_key]] = 1
    out = []
    for name in grid:
        entry = {rows_key: name}
        for column in columns:
            if column in grid[name]:
                entry[column] = grid[name][column]
        out.append(entry)
    return out
''',
        fixed='''def pivot_counts(rows: list[dict], rows_key: str, cols_key: str, columns: list[str]) -> list[dict]:
    """Count rows into a row-key by column-key grid."""
    grid: dict = {}
    for row in rows:
        cell = grid.setdefault(row[rows_key], {})
        cell[row[cols_key]] = cell.get(row[cols_key], 0) + 1
    out = []
    for name in grid:
        entry = {rows_key: name}
        for column in columns:
            entry[column] = grid[name].get(column, 0)
        out.append(entry)
    return out
''',
        base_cases=[
            [
                [[{"r": "a", "c": "x"}], "r", "c", ["x"]],
                [{"r": "a", "x": 1}],
            ]
        ],
        edge_cases=[
            [
                [[{"r": "a", "c": "x"}], "r", "c", ["x", "y"]],
                [{"r": "a", "x": 1, "y": 0}],
            ]
        ],
        subtle_cases=[
            [
                [[{"r": "a", "c": "x"}, {"r": "a", "c": "x"}], "r", "c", ["x"]],
                [{"r": "a", "x": 2}],
            ]
        ],
        instruction=(
            "`reshape.pivot.pivot_counts` leaves a column out of a row's dict when that cell\n"
            "has no rows, so the returned dicts have inconsistent keys and a consumer cannot\n"
            "line them up. Emit every requested column, with 0 where empty, per the README."
        ),
    ),
    dict(
        id="data-union-rows",
        package="setops",
        module="union",
        func="union_rows",
        contract=(
            "`union_rows(left, right, key)` concatenates both inputs and removes duplicate\n"
            "`key` values, keeping the FIRST occurrence. Field order within a row does not\n"
            "affect whether two rows are duplicates."
        ),
        buggy='''def union_rows(left: list[dict], right: list[dict], key: str) -> list[dict]:
    """Concatenate and de-duplicate on *key*, first wins."""
    out = []
    for row in left + right:
        if row not in out:
            out.append(row)
    return out
''',
        fixed='''def union_rows(left: list[dict], right: list[dict], key: str) -> list[dict]:
    """Concatenate and de-duplicate on *key*, first wins."""
    seen = set()
    out = []
    for row in left + right:
        if row[key] in seen:
            continue
        seen.add(row[key])
        out.append(row)
    return out
''',
        base_cases=[
            [[[{"id": 1, "v": "a"}], [{"id": 1, "v": "a"}], "id"], [{"id": 1, "v": "a"}]],
        ],
        edge_cases=[
            [
                [[{"id": 1, "v": "a"}], [{"id": 1, "v": "b"}], "id"],
                [{"id": 1, "v": "a"}],
            ]
        ],
        subtle_cases=[
            [
                [[{"id": 1, "v": "a"}, {"id": 1, "v": "b"}], [], "id"],
                [{"id": 1, "v": "a"}],
            ],
            [
                [[], [{"id": 2, "v": "x"}, {"id": 2, "v": "y"}], "id"],
                [{"id": 2, "v": "x"}],
            ],
        ],
        instruction=(
            "`setops.union.union_rows` de-duplicates by comparing whole rows instead of the\n"
            "`key`, so two rows with the same key but different other fields both survive.\n"
            "De-duplicate on `key` with first-wins, per the README."
        ),
    ),
    dict(
        id="data-cohort-sizes",
        package="rollup",
        module="cohort",
        func="cohort_sizes",
        contract=(
            "`cohort_sizes(users, events)` counts, per user cohort, how many distinct users\n"
            "in that cohort appear in `events`. Every cohort present in `users` appears in\n"
            "the result, with 0 when none of its users have events."
        ),
        buggy='''def cohort_sizes(users: list[dict], events: list[dict]) -> dict:
    """Distinct active users per cohort."""
    cohort_of = {user["id"]: user["cohort"] for user in users}
    counts: dict = {}
    for event in events:
        cohort = cohort_of.get(event["user_id"])
        if cohort is None:
            continue
        counts[cohort] = counts.get(cohort, 0) + 1
    return counts
''',
        fixed='''def cohort_sizes(users: list[dict], events: list[dict]) -> dict:
    """Distinct active users per cohort."""
    cohort_of = {user["id"]: user["cohort"] for user in users}
    seen: dict = {}
    for user in users:
        seen.setdefault(user["cohort"], set())
    for event in events:
        cohort = cohort_of.get(event["user_id"])
        if cohort is None:
            continue
        seen[cohort].add(event["user_id"])
    return {cohort: len(members) for cohort, members in seen.items()}
''',
        base_cases=[
            [
                [[{"id": 1, "cohort": "c1"}], [{"user_id": 1}]],
                {"c1": 1},
            ]
        ],
        edge_cases=[
            [
                [[{"id": 1, "cohort": "c1"}], [{"user_id": 1}, {"user_id": 1}]],
                {"c1": 1},
            ]
        ],
        subtle_cases=[
            [
                [[{"id": 1, "cohort": "c1"}, {"id": 2, "cohort": "c2"}], [{"user_id": 1}]],
                {"c1": 1, "c2": 0},
            ]
        ],
        instruction=(
            "`rollup.cohort.cohort_sizes` counts EVENTS rather than distinct users, so a user\n"
            "with several events inflates their cohort. Count distinct users per cohort, as\n"
            "the README describes."
        ),
    ),
    dict(
        id="data-lag-diff",
        package="series2",
        module="lag",
        func="lag_diff",
        contract=(
            "`lag_diff(rows)` sorts by `t` ascending and returns the change in `value`\n"
            "against the previous point. The first point has no predecessor and its `diff`\n"
            "is `None`."
        ),
        buggy='''def lag_diff(rows: list[dict]) -> list[dict]:
    """Change in *value* against the previous point, ordered by *t*."""
    out = []
    previous = None
    for row in rows:
        diff = None if previous is None else row["value"] - previous
        out.append({"t": row["t"], "diff": diff})
        previous = row["value"]
    return out
''',
        fixed='''def lag_diff(rows: list[dict]) -> list[dict]:
    """Change in *value* against the previous point, ordered by *t*."""
    out = []
    previous = None
    for row in sorted(rows, key=lambda item: item["t"]):
        diff = None if previous is None else row["value"] - previous
        out.append({"t": row["t"], "diff": diff})
        previous = row["value"]
    return out
''',
        base_cases=[
            [
                [[{"t": 1, "value": 10}, {"t": 2, "value": 13}]],
                [{"t": 1, "diff": None}, {"t": 2, "diff": 3}],
            ]
        ],
        edge_cases=[
            [
                [[{"t": 2, "value": 13}, {"t": 1, "value": 10}]],
                [{"t": 1, "diff": None}, {"t": 2, "diff": 3}],
            ]
        ],
        subtle_cases=[
            [
                [[{"t": 3, "value": 6}, {"t": 1, "value": 1}, {"t": 2, "value": 4}]],
                [{"t": 1, "diff": None}, {"t": 2, "diff": 3}, {"t": 3, "diff": 2}],
            ]
        ],
        instruction=(
            "`series2.lag.lag_diff` trusts the input order, so a series that arrives unsorted\n"
            "produces differences against the wrong neighbour. Sort by `t` ascending first,\n"
            "as the README states; the `None` for the first point is already right."
        ),
    ),
    dict(
        id="data-weighted-avg",
        package="rollup",
        module="wavg",
        func="weighted_avg",
        contract=(
            "`weighted_avg(rows)` returns the `value`-by-`weight` weighted mean rounded to\n"
            "4 decimals. When the total weight is zero the mean is undefined and reported\n"
            "as `None`."
        ),
        buggy='''def weighted_avg(rows: list[dict]):
    """Weighted mean of *value* by *weight*."""
    total_weight = sum(row["weight"] for row in rows)
    numerator = sum(row["value"] * row["weight"] for row in rows)
    if not rows:
        return None
    return round(numerator / total_weight, 4) if total_weight else 0.0
''',
        fixed='''def weighted_avg(rows: list[dict]):
    """Weighted mean of *value* by *weight*."""
    total_weight = sum(row["weight"] for row in rows)
    if not total_weight:
        return None
    numerator = sum(row["value"] * row["weight"] for row in rows)
    return round(numerator / total_weight, 4)
''',
        base_cases=[
            [[[{"value": 10, "weight": 1}, {"value": 20, "weight": 3}]], 17.5],
            [[[]], None],
        ],
        edge_cases=[
            [[[{"value": 10, "weight": 0}]], None],
            [[[{"value": 5, "weight": 0}, {"value": 7, "weight": 0}]], None],
        ],
        subtle_cases=[[[[{"value": 4, "weight": 2}, {"value": 6, "weight": -2}]], None]],
        instruction=(
            "`rollup.wavg.weighted_avg` returns `0.0` when the total weight is zero, which a\n"
            "consumer cannot tell apart from a genuine zero mean. Report an undefined mean as\n"
            "`None`, per the README."
        ),
    ),
    dict(
        id="data-rows-per-partition",
        package="rollup",
        module="parts",
        func="rows_per_partition",
        contract=(
            "`rows_per_partition(rows, partitions)` returns `{partition: count}` covering\n"
            "every partition in `partitions`, with 0 for the empty ones. A row whose\n"
            'partition is `None` counts under the `"__unpartitioned__"` key.'
        ),
        buggy='''UNPARTITIONED = "__unpartitioned__"


def rows_per_partition(rows: list[dict], partitions: list[str]) -> dict:
    """Row count per partition, zero-filled over *partitions*."""
    counts = {name: 0 for name in partitions}
    for row in rows:
        name = row["partition"]
        if name in counts:
            counts[name] += 1
    return counts
''',
        fixed='''UNPARTITIONED = "__unpartitioned__"


def rows_per_partition(rows: list[dict], partitions: list[str]) -> dict:
    """Row count per partition, zero-filled over *partitions*."""
    counts = {name: 0 for name in partitions}
    for row in rows:
        name = row["partition"]
        if name is None:
            counts[UNPARTITIONED] = counts.get(UNPARTITIONED, 0) + 1
        elif name in counts:
            counts[name] += 1
    return counts
''',
        base_cases=[
            [[[{"partition": "p1"}], ["p1", "p2"]], {"p1": 1, "p2": 0}],
        ],
        edge_cases=[
            [
                [[{"partition": None}], ["p1"]],
                {"p1": 0, "__unpartitioned__": 1},
            ]
        ],
        subtle_cases=[
            [
                [[{"partition": None}, {"partition": "p1"}, {"partition": None}], ["p1"]],
                {"p1": 1, "__unpartitioned__": 2},
            ]
        ],
        instruction=(
            "`rollup.parts.rows_per_partition` silently discards a row whose partition is\n"
            "`None`, so the counts do not add up to the number of input rows. Count those\n"
            "rows under the `__unpartitioned__` key the README defines."
        ),
    ),
    dict(
        id="data-normalize-keys",
        package="cleanse",
        module="keys",
        func="normalize_keys",
        contract=(
            "`normalize_keys(rows, field)` lower-cases and strips `field` on every row.\n"
            "A value that is empty after stripping is not a usable key and becomes `None`."
        ),
        buggy='''def normalize_keys(rows: list[dict], field: str) -> list[dict]:
    """Lower-case and strip *field* on every row."""
    out = []
    for row in rows:
        copy = dict(row)
        copy[field] = row[field].strip()
        out.append(copy)
    return out
''',
        fixed='''def normalize_keys(rows: list[dict], field: str) -> list[dict]:
    """Lower-case and strip *field* on every row."""
    out = []
    for row in rows:
        copy = dict(row)
        value = row[field].strip().lower()
        copy[field] = value or None
        out.append(copy)
    return out
''',
        base_cases=[[[[{"k": " abc "}], "k"], [{"k": "abc"}]]],
        edge_cases=[
            [[[{"k": "ABC"}], "k"], [{"k": "abc"}]],
            [[[{"k": " MiXeD "}], "k"], [{"k": "mixed"}]],
        ],
        subtle_cases=[[[[{"k": "   "}], "k"], [{"k": None}]], [[[{"k": ""}], "k"], [{"k": None}]]],
        instruction=(
            "`cleanse.keys.normalize_keys` strips but never lower-cases, so `ABC` and `abc`\n"
            "stay distinct keys downstream. Fold the case as the README requires."
        ),
    ),
    dict(
        id="data-rolling-max",
        package="series2",
        module="window",
        func="rolling_max",
        contract=(
            "`rolling_max(values, size)` returns the maximum of each full window of `size`\n"
            "consecutive values, so a series of n values yields `n - size + 1` entries.\n"
            "A window larger than the series yields an empty list."
        ),
        buggy='''def rolling_max(values: list[float], size: int) -> list[float]:
    """Maximum of each full window of *size* consecutive values."""
    out = []
    for start in range(len(values) - size):
        out.append(max(values[start : start + size]))
    return out
''',
        fixed='''def rolling_max(values: list[float], size: int) -> list[float]:
    """Maximum of each full window of *size* consecutive values."""
    out = []
    for start in range(len(values) - size + 1):
        out.append(max(values[start : start + size]))
    return out
''',
        base_cases=[[[[], 2], []], [[[1, 2], 5], []]],
        edge_cases=[[[[1, 5, 3, 9], 2], [5, 5, 9]], [[[2, 2, 2], 3], [2]]],
        subtle_cases=[[[[4], 1], [4]], [[[7, 7], 2], [7]]],
        instruction=(
            "`series2.window.rolling_max` stops one window early, so the last full window is\n"
            "missing and the result is shorter than `n - size + 1`. Emit every full window\n"
            "per the README; an over-long window still yields an empty list."
        ),
    ),
    dict(
        id="data-reconcile",
        package="recon",
        module="diff",
        func="reconcile",
        contract=(
            "`reconcile(expected, actual)` returns `{key: actual - expected}` for every key\n"
            "present on EITHER side, treating a missing side as 0, and omits keys whose\n"
            "difference is zero."
        ),
        buggy='''def reconcile(expected: dict, actual: dict) -> dict:
    """Signed difference actual - expected, per key."""
    out: dict = {}
    for key, value in expected.items():
        delta = value - actual.get(key, 0)
        if delta:
            out[key] = delta
    return out
''',
        fixed='''def reconcile(expected: dict, actual: dict) -> dict:
    """Signed difference actual - expected, per key."""
    out: dict = {}
    for key in set(expected) | set(actual):
        delta = actual.get(key, 0) - expected.get(key, 0)
        if delta:
            out[key] = delta
    return out
''',
        base_cases=[[[{"a": 5}, {"a": 5}], {}]],
        edge_cases=[[[{"a": 5}, {"a": 8}], {"a": 3}], [[{"a": 10}, {"a": 4}], {"a": -6}]],
        subtle_cases=[[[{}, {"b": 2}], {"b": 2}], [[{"a": 1}, {"b": 2}], {"a": -1, "b": 2}]],
        instruction=(
            "`recon.diff.reconcile` reports the difference with the sign inverted -- it\n"
            "computes expected minus actual where the README defines actual minus expected.\n"
            "Correct the direction; the zero-difference omission already behaves."
        ),
    ),
]
