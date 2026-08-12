def normalize_keys(rows: list[dict], field: str) -> list[dict]:
    """Lower-case and strip *field* on every row."""
    out = []
    for row in rows:
        copy = dict(row)
        copy[field] = row[field].strip()
        out.append(copy)
    return out
