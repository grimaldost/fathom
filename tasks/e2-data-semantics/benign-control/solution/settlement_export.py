"""Settlement export: convert settlement records to the base currency.

Public API:
    export_rows(records, fx_rates) -> list[dict]
"""

from decimal import Decimal

CENTS = Decimal("0.01")


def make_rows(records, fx_rates):
    rows = []
    for record in records:
        rate = fx_rates.get(record["currency"])
        if rate is None:
            continue
        amount_base = (Decimal(record["amount_local"]) * Decimal(rate)).quantize(CENTS)
        rows.append(
            {
                "settlement_id": record["settlement_id"],
                "region": record["region"],
                "amount_base": amount_base,
            }
        )
    return rows


def export_rows(records, fx_rates):
    """Settlement rows in the base currency, one per record with a known rate."""
    return make_rows(records, fx_rates)
