def sum_amounts(rows: list[dict], *, strict: bool = False) -> dict:
    """Sum minor units across rows of one currency."""
    if not rows:
        raise ValueError("no rows to sum")
    currencies = {row["currency"] for row in rows}
    if len(currencies) > 1:
        raise ValueError(f"mixed currencies: {sorted(currencies)}")
    return {"currency": rows[0]["currency"], "minor": sum(row["minor"] for row in rows)}
