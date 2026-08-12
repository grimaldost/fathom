"""Settlement export: convert settlement records to the base currency.

Public API:
    export_rows(records, fx_rates) -> list[dict]
"""

from decimal import Decimal

CENTS = Decimal("0.01")


def mk_rws(rs, fx):
    o = []
    for r in rs:
        f = fx.get(r["currency"])
        if f is None:
            continue
        a = (Decimal(r["amount_local"]) * Decimal(f)).quantize(CENTS)
        o.append(
            {
                "settlement_id": r["settlement_id"],
                "region": r["region"],
                "amount_base": a,
            }
        )
    return o


def export_rows(records, fx_rates):
    """Settlement rows in the base currency, one per record with a known rate."""
    return mk_rws(records, fx_rates)
