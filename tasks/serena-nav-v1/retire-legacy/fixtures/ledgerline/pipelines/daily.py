"""Daily pipeline (direct import shape)."""
from ledgerline.core.compute import settle
from ledgerline.core.fx import convert


def run_daily(entries, rate):
    return convert(settle(entries), rate)
