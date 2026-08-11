def total_by(rows: list[dict], key: str, field: str, *, strict: bool = False) -> dict:
    """Sum *field* per distinct *key* value."""
    totals: dict = {}
    for row in rows:
        if field not in row:
            raise KeyError(field)
        value = row[field] or 0
        totals[row[key]] = totals.get(row[key], 0) + value
    return totals
