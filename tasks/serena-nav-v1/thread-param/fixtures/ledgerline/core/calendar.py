"""Business-date helpers."""
from datetime import timedelta


def roll_date(d, days):
    return d + timedelta(days=days)


def is_weekend(d):
    return d.weekday() >= 5
