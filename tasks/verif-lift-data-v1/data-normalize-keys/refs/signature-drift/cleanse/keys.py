def normalize_keys(rows: list[dict], field: str, *, strict: bool = False) -> list[dict]:
    """Lower-case and strip *field* on every row."""
    out = []
    for row in rows:
        copy = dict(row)
        value = row[field].strip().lower()
        copy[field] = value or None
        out.append(copy)
    return out
