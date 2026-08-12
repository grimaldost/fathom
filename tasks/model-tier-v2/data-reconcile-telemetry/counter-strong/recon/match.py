"""Match readings to registered devices."""


def match(readings, devices):
    """Return (reading_id, device_id) pairs under RULES.md M1-M3."""
    pairs = []
    used = set()
    for reading in sorted(readings, key=lambda r: (r.at, str(r.id))):
        eligible = [
            d for d in devices if d.id not in used and abs(reading.at - d.seen_at) <= d.tolerance
        ]
        if not eligible:
            continue
        best = min(
            eligible,
            key=lambda d: (abs(reading.at - d.seen_at), d.seen_at, str(d.id)),
        )
        pairs.append((reading.id, best.id))
        used.add(best.id)
    return pairs
