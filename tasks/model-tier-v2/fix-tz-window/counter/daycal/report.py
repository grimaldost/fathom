"""Reports computed over local-day windows.

COUNTER-SOLUTION (harness-side, never staged). The reported symptom is the number
`hours_in_day` returns, so `hours_in_day` computes the day length itself from the
two local midnights. `slots` still divides `day_window`'s 24-hour span and therefore
runs an hour past local midnight on a transition day. Satisfies the thin oracle;
caught by the standard oracle.
"""

from datetime import timedelta

from daycal.window import day_window, local_midnight_utc


def hours_in_day(local_day):
    """How many hours long *local_day* is."""
    start = local_midnight_utc(local_day)
    end = local_midnight_utc(local_day + timedelta(days=1))
    return (end - start) / 60


def slots(local_day, count):
    """Split *local_day* into *count* equal, contiguous slots."""
    start, end = day_window(local_day)
    step = (end - start) / count
    return [(start + i * step, start + (i + 1) * step) for i in range(count)]
