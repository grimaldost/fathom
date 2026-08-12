"""Readings the registry could not account for."""


def gaps(readings, pairs):
    """Return the ids of unmatched readings, ascending by `at` then `id` (G1)."""
    matched = {reading_id for reading_id, _device_id in pairs}
    unmatched = [r for r in readings if r.id not in matched]
    return [r.id for r in sorted(unmatched, key=lambda r: (r.at, str(r.id)))]
