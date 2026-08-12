"""The summary view."""

from feedcache import keys


def summary(store, tenant: str, day: str, totals):
    """Total of *totals* for *tenant* on *day*, cached."""
    key = keys.summary_key(tenant)
    hit = store.get(key)
    if hit is not None and hit.get("day") == day:
        return hit
    value = {"tenant": tenant, "day": day, "total": sum(totals)}
    store.put(key, value)
    return value
