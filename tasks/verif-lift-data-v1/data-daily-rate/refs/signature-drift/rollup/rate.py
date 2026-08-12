def daily_rate(rows: list[dict], *, strict: bool = False) -> dict:
    """Events per actor for each day."""
    out: dict = {}
    for row in rows:
        actors = row["actors"]
        out[row["day"]] = None if actors == 0 else round(row["events"] / actors, 3)
    return out
