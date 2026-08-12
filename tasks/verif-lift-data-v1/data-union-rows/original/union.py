def union_rows(left: list[dict], right: list[dict], key: str) -> list[dict]:
    """Concatenate and de-duplicate on *key*, first wins."""
    out = []
    for row in left + right:
        if row not in out:
            out.append(row)
    return out
