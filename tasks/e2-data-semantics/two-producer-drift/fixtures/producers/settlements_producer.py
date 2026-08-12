"""Settlement side of the region_daily contract.

Settlement records reach us by two upstream paths. The overnight `batch` export
carries a plain calendar day; the `streaming` feed carries a full timestamp, so
its day has to be derived before it can be emitted.
"""

from datetime import date, datetime
from decimal import Decimal


def _period_of(record):
    if record.get("source") == "batch":
        return date.fromisoformat(record["settled_at"][:10])
    stamp = datetime.fromisoformat(record["settled_at"])
    return stamp.replace(hour=0, minute=0, second=0, microsecond=0)


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
