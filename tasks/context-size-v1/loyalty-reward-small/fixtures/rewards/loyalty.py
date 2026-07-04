"""Loyalty program reward rates (canonical source of truth)."""

from decimal import Decimal

RATES = {"silver": Decimal("0.01"), "gold": Decimal("0.02"), "platinum": Decimal("0.05")}


def rate_for(tier):
    """Return the reward rate for a loyalty tier."""
    return RATES[tier]
