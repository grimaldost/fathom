def sum_amounts(rows: list[dict]) -> dict:
    """Sum minor units across rows of one currency."""
    total = 0
    currency = ""
    for row in rows:
        total += row["minor"]
        currency = row["currency"]
    return {"currency": currency, "minor": total}
