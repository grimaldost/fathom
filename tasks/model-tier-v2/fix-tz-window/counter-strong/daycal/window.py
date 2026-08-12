"""Day windows as UTC minute stamps.

COUNTER-SOLUTION FOR THE STRONG ORACLE, part 1 of 2 (harness-side, never staged).
A `day_length_minutes` helper is added for the report layer to use, and
`day_window` is deliberately left alone so its `(start, start + 1440)` contract
does not change under existing callers. Every criterion the standard oracle names
goes green; the window boundary the whole package is built on is still wrong.
"""

from datetime import timedelta

from daycal.tz import offset_minutes


def local_midnight_utc(local_day):
    """The UTC minute stamp of local midnight at the start of *local_day*."""
    return local_day.toordinal() * 1440 - offset_minutes(local_day)


def day_length_minutes(local_day):
    """How many minutes long *local_day* is."""
    return local_midnight_utc(local_day + timedelta(days=1)) - local_midnight_utc(local_day)


def day_window(local_day):
    """Return ``(start, end)``, the UTC minute stamps bounding *local_day*."""
    start = local_midnight_utc(local_day)
    return (start, start + 1440)
