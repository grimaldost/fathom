def left_join(left: list[dict], right: list[dict], key: str) -> list[dict]:
    """Left join *left* onto *right* on *key*."""
    index: dict = {}
    for row in right:
        index.setdefault(row[key], []).append(row)
    out = []
    for row in left:
        matches = index.get(row[key], [])
        if not matches:
            merged = dict(row)
            merged.setdefault("tag", None)
            out.append(merged)
            continue
        for match in matches:
            merged = dict(row)
            if "tag" not in merged:
                merged["tag"] = match["tag"]
            out.append(merged)
    return out
