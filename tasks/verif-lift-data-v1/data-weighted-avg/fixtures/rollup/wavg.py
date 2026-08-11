def weighted_avg(rows: list[dict]):
    """Weighted mean of *value* by *weight*."""
    total_weight = sum(row["weight"] for row in rows)
    numerator = sum(row["value"] * row["weight"] for row in rows)
    if not rows:
        return None
    return round(numerator / total_weight, 4) if total_weight else 0.0
