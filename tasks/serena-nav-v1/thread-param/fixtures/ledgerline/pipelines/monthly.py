"""Monthly pipeline (module-alias import shape)."""
import ledgerline.core.compute as cc
from ledgerline.core.fx import convert


def run_monthly(batches, rate):
    return convert(sum(cc.settle(b) for b in batches), rate)
