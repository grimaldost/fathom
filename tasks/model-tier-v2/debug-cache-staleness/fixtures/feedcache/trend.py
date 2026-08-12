"""The trend view."""

from feedcache import keys


def trend(store, tenant: str, day: str, series):
    """Direction of *series* for *tenant* on *day*, cached."""
    key = keys.trend_key(tenant)
    hit = store.get(key)
    if hit is not None:
        return hit
    direction = "up" if len(series) > 1 and series[-1] > series[0] else "flat"
    value = {"tenant": tenant, "day": day, "direction": direction}
    store.put(key, value)
    return value
