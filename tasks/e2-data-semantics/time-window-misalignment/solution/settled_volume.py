"""Monthly settled volume for the settlement desk.

Every time-based decision here is made on event time in UTC (contract: Time
semantics) -- the window bound AND the rate key, so both sides of the join are
filtered on the same clock. `load_date` is an ingestion column and no metric is
defined on it.

Public API:
    monthly_volume(orders, fx_rates, year, month) -> {"total": Decimal, "order_ids": [str]}
"""

from datetime import UTC, datetime
from decimal import Decimal


def event_day_utc(order):
    """The order's event date in UTC, as YYYY-MM-DD."""
    return datetime.fromisoformat(order["event_ts"]).astimezone(UTC).date().isoformat()


def _in_month(day, year, month):
    return day[:7] == f"{year:04d}-{month:02d}"


def _rate_for(order, fx_rates):
    """The rate whose rate_date is the order's event date in UTC."""
    day = event_day_utc(order)
    for rate in fx_rates:
        if rate["currency"] == order["currency"] and rate["rate_date"] == day:
            return Decimal(rate["rate"])
    return None


def monthly_volume(orders, fx_rates, year, month):
    """Total converted volume for a calendar month, and the orders behind it."""
    total = Decimal("0.00")
    order_ids = []
    for order in orders:
        if not _in_month(event_day_utc(order), year, month):
            continue
        rate = _rate_for(order, fx_rates)
        if rate is None:
            continue
        total += Decimal(order["amount_local"]) * rate
        order_ids.append(order["order_id"])
    return {"total": total, "order_ids": order_ids}
