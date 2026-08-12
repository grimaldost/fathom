"""Reports computed over local-day windows."""

from daycal.window import day_window


def hours_in_day(local_day):
    """How many hours long *local_day* is."""
    start, end = day_window(local_day)
    return (end - start) / 60


def slots(local_day, count):
    """Split *local_day* into *count* equal, contiguous slots."""
    start, end = day_window(local_day)
    step = (end - start) / count
    return [(start + i * step, start + (i + 1) * step) for i in range(count)]
