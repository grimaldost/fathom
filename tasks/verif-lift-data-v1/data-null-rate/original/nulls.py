def null_rate(rows: list[dict], field: str) -> float:
    """Share of rows whose *field* is null-ish."""
    nulls = sum(1 for row in rows if row.get(field) is None)
    return round(nulls / len(rows), 3) if rows else 0.0
