"""Readings the registry could not account for."""


def gaps(readings, pairs):
    """Return the ids of unmatched readings, one per timestamp, ascending."""
    matched = {reading_id for reading_id, _device_id in pairs}
    unmatched = [r for r in readings if r.id not in matched]
    seen = set()
    out = []
    for reading in sorted(unmatched, key=lambda r: (r.at, str(r.id))):
        if reading.at in seen:
            continue
        seen.add(reading.at)
        out.append(reading.id)
    return out
