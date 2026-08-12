"""Settlement side of the region_daily contract.

Settlement records reach us by two upstream paths. The overnight `batch` export
carries a plain calendar day; the `streaming` feed carries a full timestamp.
Both paths emit the contract's `period` column as a `datetime.date`, which is
what the other producer of that column emits and what `reconcile()` joins on.
"""

from datetime import date, datetime
from decimal import Decimal


def _period_of(record):
    if record.get("source") == "batch":
        return date.fromisoformat(record["settled_at"][:10])
    return datetime.fromisoformat(record["settled_at"]).date()


def emit(raw_settlements):
    """Aggregate raw settlement records into region_daily settlement rows.

    Each raw record:
    {"region": str, "settled_at": str, "amount": str, "source": "batch" | "streaming"}
    """
    totals = {}
    for record in raw_settlements:
        key = (record["region"], _period_of(record))
        totals[key] = totals.get(key, Decimal("0.00")) + Decimal(record["amount"])

    return [
        {"region": region, "period": period, "settled_amount": amount}
        for (region, period), amount in sorted(
            totals.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))
        )
    ]
