def to_weekly(rows: list[dict], weeks: list[str], *, strict: bool = False) -> list[dict]:
    """One summed entry per week in *weeks*."""
    totals: dict = {}
    for row in rows:
        totals[row["week"]] = totals.get(row["week"], 0) + row["amount"]
    return [{"week": week, "amount": totals.get(week, 0)} for week in weeks]
