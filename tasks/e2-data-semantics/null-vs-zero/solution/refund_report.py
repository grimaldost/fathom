"""Regional refund report.

`refund_total` and `refund_count` are non-nullable (contract: Zero is a value).
A region with no refund rows and a region whose rows net to zero both report
`0.00`; only their counts differ.

Public API:
    build_report(regions, refunds) -> list[dict]
"""

from decimal import Decimal


def build_report(regions, refunds):
    """One row per region: net refunds and the number of refund rows."""
    grouped = {}
    for refund in refunds:
        grouped.setdefault(refund["region"], []).append(refund)

    report = []
    for region in regions:
        rows = grouped.get(region, [])
        total = sum((Decimal(r["amount"]) for r in rows), Decimal("0.00"))
        report.append(
            {
                "region": region,
                "refund_total": total,
                "refund_count": len(rows),
            }
        )
    return report
