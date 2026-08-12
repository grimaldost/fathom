"""Convert US/Eastern wall-clock times to UTC."""

from datetime import datetime, timedelta


def to_utc(year, month, day, hour, minute=0):
    """Convert a naive US/Eastern local time to a UTC ISO-8601 ``Z`` timestamp.

    US/Eastern observes daylight saving time (UTC-4) in summer and standard time
    (UTC-5) in winter.
    """
    is_dst = 4 <= month <= 10
    offset_hours = 4 if is_dst else 5
    local = datetime(year, month, day, hour, minute)
    utc = local + timedelta(hours=offset_hours)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
