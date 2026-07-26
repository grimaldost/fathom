"""Analytics: ratios."""
from ledgerline.utils.textfmt import fmt_amount


def ratios_metric(values):
    return fmt_amount(sum(values))
