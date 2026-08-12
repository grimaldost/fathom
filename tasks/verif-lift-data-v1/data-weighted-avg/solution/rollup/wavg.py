def weighted_avg(rows: list[dict]):
    """Weighted mean of *value* by *weight*."""
    total_weight = sum(row["weight"] for row in rows)
    if not total_weight:
        return None
    numerator = sum(row["value"] * row["weight"] for row in rows)
    return round(numerator / total_weight, 4)
