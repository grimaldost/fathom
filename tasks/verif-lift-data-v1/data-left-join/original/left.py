def left_join(left: list[dict], right: list[dict], key: str) -> list[dict]:
    """Left join *left* onto *right* on *key*."""
    index = {row[key]: row for row in right}
    out = []
    for row in left:
        match = index.get(row[key])
        merged = dict(row)
        merged["tag"] = match["tag"] if match else None
        out.append(merged)
    return out
