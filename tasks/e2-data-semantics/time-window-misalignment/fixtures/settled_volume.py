"""Monthly settled volume for the settlement desk.

Public API:
    monthly_volume(orders, fx_rates, year, month) -> {"total": Decimal, "order_ids": [str]}
"""

from decimal import Decimal


def _in_month(day, year, month):
    return day[:7] == f"{year:04d}-{month:02d}"


def _rate_for(order, fx_rates):
    """The rate to apply to *order*."""
    for rate in fx_rates:
        if rate["currency"] == order["currency"] and rate["rate_date"] == order["load_date"]:
            return Decimal(rate["rate"])
    return None


def monthly_volume(orders, fx_rates, year, month):
    """Total converted volume for a calendar month, and the orders behind it."""
    total = Decimal("0.00")
    order_ids = []
    for order in orders:
        if not _in_month(order["load_date"], year, month):
            continue
        rate = _rate_for(order, fx_rates)
        if rate is None:
            continue
        total += Decimal(order["amount_local"]) * rate
        order_ids.append(order["order_id"])
    return {"total": total, "order_ids": order_ids}
