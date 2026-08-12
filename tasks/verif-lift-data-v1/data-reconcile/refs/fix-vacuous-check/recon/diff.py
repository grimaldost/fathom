def reconcile(expected: dict, actual: dict) -> dict:
    """Signed difference actual - expected, per key."""
    out: dict = {}
    for key in set(expected) | set(actual):
        delta = actual.get(key, 0) - expected.get(key, 0)
        if delta:
            out[key] = delta
    return out
