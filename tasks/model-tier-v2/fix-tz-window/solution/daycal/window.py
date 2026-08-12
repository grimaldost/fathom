"""Day windows as UTC minute stamps."""

from datetime import timedelta

from daycal.tz import offset_minutes


def local_midnight_utc(local_day):
    """The UTC minute stamp of local midnight at the start of *local_day*."""
    return local_day.toordinal() * 1440 - offset_minutes(local_day)


def day_window(local_day):
    """Return ``(start, end)``, the UTC minute stamps bounding *local_day*."""
    start = local_midnight_utc(local_day)
    end = local_midnight_utc(local_day + timedelta(days=1))
    return (start, end)
