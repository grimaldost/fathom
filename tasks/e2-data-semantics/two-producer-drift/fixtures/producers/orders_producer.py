"""Order side of the region_daily contract.

Emits one row per (region, order day) with the day's gross amount.
"""

from datetime import date
from decimal import Decimal


def emit(raw_orders):
    """Aggregate raw order records into region_daily order rows.

    Each raw record: {"region": str, "order_date": "YYYY-MM-DD", "amount": str}
    """
    totals = {}
    for record in raw_orders:
        key = (record["region"], date.fromisoformat(record["order_date"]))
        totals[key] = totals.get(key, Decimal("0.00")) + Decimal(record["amount"])

    return [
        {"region": region, "period": period, "gross_amount": amount}
        for (region, period), amount in sorted(
            totals.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))
        )
    ]
