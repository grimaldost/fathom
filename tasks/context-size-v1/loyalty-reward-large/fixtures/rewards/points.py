"""Reward points calculation."""

from decimal import Decimal


def reward(customer_id, spend):
    """Reward credit earned for a given customer and spend amount."""
    spend = Decimal(spend)
    return spend * Decimal("0.01")
