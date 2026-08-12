def pct_share(rows: list[dict]) -> dict:
    """Each row's percentage share of the total."""
    total = sum(row["value"] for row in rows)
    return {row["name"]: round(row["value"], 2) for row in rows} if not total else {
        row["name"]: round(100.0 * row["value"] / total, 2) for row in rows
    }
