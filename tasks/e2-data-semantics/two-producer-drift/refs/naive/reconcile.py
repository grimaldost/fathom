"""Assemble the region_daily rows from the two producers.

NAIVE REFERENCE — the fix a first pass reaches for: the join was dropping rows,
so normalise the key at the join site. The reconciliation fills back in and the
shipped suite stays green, but the two producers still emit different types for
the same contract column, so every other consumer of that column is still broken.
"""

from datetime import datetime


def _period_key(value):
    return value.date() if isinstance(value, datetime) else value


def reconcile(order_rows, settlement_rows):
    """Inner-join the two producers' output on (region, period)."""
    settled = {
        (row["region"], _period_key(row["period"])): row["settled_amount"]
        for row in settlement_rows
    }

    assembled = []
    for row in order_rows:
        key = (row["region"], _period_key(row["period"]))
        if key not in settled:
            continue
        assembled.append(
            {
                "region": row["region"],
                "period": row["period"],
                "gross_amount": row["gross_amount"],
                "settled_amount": settled[key],
            }
        )
    return assembled
