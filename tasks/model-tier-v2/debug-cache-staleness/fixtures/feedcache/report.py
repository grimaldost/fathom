"""The daily report view."""

from feedcache import keys


def daily_report(store, tenant: str, day: str, rows):
    """Row count and total for *tenant* on *day*, cached."""
    key = keys.report_key(tenant)
    hit = store.get(key)
    if hit is not None:
        return hit
    value = {"tenant": tenant, "day": day, "rows": len(rows), "total": sum(rows)}
    store.put(key, value)
    return value
