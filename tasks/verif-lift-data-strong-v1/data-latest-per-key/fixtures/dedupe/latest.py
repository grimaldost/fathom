def latest_per_key(rows: list[dict], key: str) -> list[dict]:
    """Keep the greatest-*ts* row per *key*."""
    best: dict = {}
    for row in rows:
        current = best.get(row[key])
        if current is None or row["ts"] > current["ts"]:
            best[row[key]] = row
    return [best[k] for k in best]
