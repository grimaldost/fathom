"""Match readings to registered devices."""


def match(readings, devices):
    """Return a list of (reading_id, device_id) pairs.

    Current behaviour: for each reading in order, take the first device whose
    `seen_at` is strictly within its tolerance, and never reuse a device.
    """
    pairs = []
    used = set()
    for reading in readings:
        for device in devices:
            if device.id in used:
                continue
            if abs(reading.at - device.seen_at) < device.tolerance:
                pairs.append((reading.id, device.id))
                used.add(device.id)
                break
    return pairs
