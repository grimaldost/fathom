"""Timestamp parsing and normalization."""

from datetime import datetime, timezone


def parse_timestamp(text):
    """Parse an ISO-8601 timestamp into a timezone-aware UTC datetime."""
    text = text.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize(text):
    """Normalize a timestamp string to canonical UTC ISO-8601 with a Z suffix."""
    return parse_timestamp(text).strftime("%Y-%m-%dT%H:%M:%SZ")
