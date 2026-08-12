"""Match readings to registered devices."""


def match(readings, devices):
    """Return a list of (reading_id, device_id) pairs."""
    pairs = []
    used = set()
    for reading in sorted(readings, key=lambda r: (r.at, str(r.id))):
        for device in devices:
            if device.id in used:
                continue
            if abs(reading.at - device.seen_at) < device.tolerance:
                pairs.append((reading.id, device.id))
                used.add(device.id)
                break
    return pairs
