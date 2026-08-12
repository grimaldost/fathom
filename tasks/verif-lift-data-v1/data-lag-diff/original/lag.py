def lag_diff(rows: list[dict]) -> list[dict]:
    """Change in *value* against the previous point, ordered by *t*."""
    out = []
    previous = None
    for row in rows:
        diff = None if previous is None else row["value"] - previous
        out.append({"t": row["t"], "diff": diff})
        previous = row["value"]
    return out
