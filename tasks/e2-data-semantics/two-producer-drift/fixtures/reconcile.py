"""Assemble the region_daily rows from the two producers.

Joins on the shared `(region, period)` key with no coercion: the contract says
both producers commit to the same representation of `period`.
"""


def reconcile(order_rows, settlement_rows):
    """Inner-join the two producers' output on (region, period)."""
    settled = {(row["region"], row["period"]): row["settled_amount"] for row in settlement_rows}

    assembled = []
    for row in order_rows:
        key = (row["region"], row["period"])
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
