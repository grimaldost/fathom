def total_by(rows: list[dict], key: str, field: str) -> dict:
    """Sum *field* per distinct *key* value."""
    totals: dict = {}
    for row in rows:
        value = row.get(field) or 0
        if not value:
            continue
        totals[row[key]] = totals.get(row[key], 0) + value
    return totals
