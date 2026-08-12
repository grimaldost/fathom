def null_rate(rows: list[dict], field: str):
    """Share of rows whose *field* is null-ish."""
    if not rows:
        return None
    nulls = 0
    for row in rows:
        value = row.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            nulls += 1
    return round(nulls / len(rows), 3)
