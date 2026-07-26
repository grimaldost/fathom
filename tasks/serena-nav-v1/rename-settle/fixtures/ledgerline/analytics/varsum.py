"""Analytics: varsum."""
from ledgerline.utils.textfmt import fmt_amount


def varsum_metric(values):
    return fmt_amount(sum(values))
