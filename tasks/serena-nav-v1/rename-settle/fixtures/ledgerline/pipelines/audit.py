"""Accrual audit pipeline."""
from ledgerline.core.compute import accrue


def audit_accruals(positions):
    return [accrue(p["principal"], p["rate"], p["days"]) for p in positions]
