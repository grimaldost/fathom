def reconcile(expected: dict, actual: dict) -> dict:
    """Signed difference actual - expected, per key."""
    out: dict = {}
    for key, value in expected.items():
        delta = value - actual.get(key, 0)
        if delta:
            out[key] = delta
    return out
