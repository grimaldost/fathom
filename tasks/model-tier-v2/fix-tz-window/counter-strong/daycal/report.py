"""Reports computed over local-day windows.

COUNTER-SOLUTION FOR THE STRONG ORACLE, part 2 of 2 (harness-side, never staged).
Both consumers now ask `window.day_length_minutes` how long the day is instead of
subtracting the window bounds, so both report the right answer while `day_window`
stays wrong.
"""

from daycal.window import day_length_minutes, local_midnight_utc


def hours_in_day(local_day):
    """How many hours long *local_day* is."""
    return day_length_minutes(local_day) / 60


def slots(local_day, count):
    """Split *local_day* into *count* equal, contiguous slots."""
    start = local_midnight_utc(local_day)
    step = day_length_minutes(local_day) / count
    return [(start + i * step, start + (i + 1) * step) for i in range(count)]
