def to_weekly(rows: list[dict], weeks: list[str]) -> list[dict]:
    """One summed entry per week in *weeks*."""
    totals: dict = {}
    for row in rows:
        totals[row["week"]] = totals.get(row["week"], 0) + row["amount"]
    return [{"week": week, "amount": totals[week]} for week in weeks if week in totals]
