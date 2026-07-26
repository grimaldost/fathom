"""Validator: nulls (routes through the legacy surface)."""
from ledgerline.legacy import oldapi


def check_nulls(entries):
    return oldapi.legacy_total(entries) >= 0
