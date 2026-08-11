def union_rows(left: list[dict], right: list[dict], key: str) -> list[dict]:
    """Concatenate and de-duplicate on *key*, first wins."""
    seen = set()
    out = []
    for row in left + right:
        if row[key] in seen:
            continue
        seen.add(row[key])
        out.append(row)
    return out
