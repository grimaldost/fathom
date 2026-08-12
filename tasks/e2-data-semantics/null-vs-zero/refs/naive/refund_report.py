"""Regional refund report.

NAIVE REFERENCE -- the fix a first pass reaches for: regions with no refunds were
coming back null, so give them their own branch that reports zero. The visible
symptom goes away. The remaining path still tests the total for truth, so a region
whose refunds net to zero -- a refund and its reversal -- keeps coming back null,
with its row count lost as well.

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
        if not rows:
            report.append({"region": region, "refund_total": Decimal("0.00"), "refund_count": 0})
            continue
        total = sum((Decimal(r["amount"]) for r in rows), Decimal("0.00"))
        report.append(
            {
                "region": region,
                "refund_total": total if total else None,
                "refund_count": len(rows) if total else None,
            }
        )
    return report
