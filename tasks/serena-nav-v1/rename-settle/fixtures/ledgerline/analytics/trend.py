"""Analytics: trend (routes through the legacy surface)."""
from ledgerline.legacy import oldapi


def trend_metric(entries):
    return oldapi.legacy_total(entries) / max(len(entries), 1)
