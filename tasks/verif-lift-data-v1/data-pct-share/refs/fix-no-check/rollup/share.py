def pct_share(rows: list[dict]) -> dict:
    """Each row's percentage share of the total."""
    values = {row["name"]: row["value"] or 0 for row in rows}
    total = sum(values.values())
    if not total:
        return dict.fromkeys(values, 0.0)
    return {name: round(100.0 * value / total, 2) for name, value in values.items()}
