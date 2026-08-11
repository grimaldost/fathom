"""Regional refund report.

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
        rows = grouped.get(region)
        total = sum((Decimal(r["amount"]) for r in rows), Decimal("0.00")) if rows else None
        report.append(
            {
                "region": region,
                "refund_total": total if total else None,
                "refund_count": len(rows) if total else None,
            }
        )
    return report
