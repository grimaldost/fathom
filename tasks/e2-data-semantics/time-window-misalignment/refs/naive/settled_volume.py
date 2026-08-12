"""Monthly settled volume for the settlement desk.

NAIVE REFERENCE -- the fix a first pass reaches for: the month filter was reading
the load day instead of when the order actually happened, so switch the window to
event time. The right orders are now in the statement. The rate lookup is a
separate function and still keys on `load_date`, so any order whose local load
day differs from its UTC event day is converted at the wrong day's rate.

Public API:
    monthly_volume(orders, fx_rates, year, month) -> {"total": Decimal, "order_ids": [str]}
"""

from datetime import UTC, datetime
from decimal import Decimal


def _event_day_utc(order):
    return datetime.fromisoformat(order["event_ts"]).astimezone(UTC).date().isoformat()


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
        if not _in_month(_event_day_utc(order), year, month):
            continue
        rate = _rate_for(order, fx_rates)
        if rate is None:
            continue
        total += Decimal(order["amount_local"]) * rate
        order_ids.append(order["order_id"])
    return {"total": total, "order_ids": order_ids}
