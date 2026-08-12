def daily_rate(rows: list[dict]) -> dict:
    """Events per actor for each day."""
    out: dict = {}
    for row in rows:
        out[row["day"]] = round(row["events"] / max(row["actors"], 1), 3)
    return out
