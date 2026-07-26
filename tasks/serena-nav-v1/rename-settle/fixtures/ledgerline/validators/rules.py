"""Validator: rules (routes through the legacy surface)."""
from ledgerline.legacy import oldapi


def check_rules(entries):
    return oldapi.legacy_total(entries) >= 0
