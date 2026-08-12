"""The daily report view."""

from feedcache import keys


def daily_report(store, tenant: str, day: str, data):
    """Cached, scoped to (tenant, day)."""
    key = keys.report_key(tenant, day)
    hit = store.get(key)
    if hit is not None:
        return hit
    value = {"tenant": tenant, "day": day, "rows": len(data), "total": sum(data)}
    store.put(key, value)
    return value
