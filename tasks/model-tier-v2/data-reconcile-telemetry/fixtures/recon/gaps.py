"""Readings the registry could not account for."""


def gaps(readings, pairs):
    """Return the ids of readings with no match, in the order they were read."""
    matched = [reading_id for reading_id, _device_id in pairs]
    return [r.id for r in readings if r.id not in matched]
