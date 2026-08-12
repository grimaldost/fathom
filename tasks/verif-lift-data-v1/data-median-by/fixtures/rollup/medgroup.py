def median_by(rows: list[dict], key: str) -> dict:
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
