"""The summary view."""

from feedcache import keys


def summary(store, tenant: str, day: str, data):
    """Cached, scoped to (tenant, day)."""
    key = keys.summary_key(tenant, day)
    hit = store.get(key)
    if hit is not None:
        return hit
    value = {"tenant": tenant, "day": day, "total": sum(data)}
    store.put(key, value)
    return value
