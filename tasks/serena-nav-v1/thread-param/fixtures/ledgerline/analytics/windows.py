"""Analytics: windows."""
from ledgerline.utils.textfmt import fmt_amount


def windows_metric(values):
    return fmt_amount(sum(values))
