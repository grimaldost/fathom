def median_by(rows: list[dict], key: str) -> dict:
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
