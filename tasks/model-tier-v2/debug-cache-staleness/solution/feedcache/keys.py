"""Cache keys for the feed views."""


def summary_key(tenant: str, day: str) -> str:
    """Key for the summary view, scoped to the day it answers about."""
    return f"summary:{tenant}:{day}"


def report_key(tenant: str, day: str) -> str:
    """Key for the daily report view, scoped to the day it answers about."""
    return f"report:{tenant}:{day}"


def trend_key(tenant: str, day: str) -> str:
    """Key for the trend view, scoped to the day it answers about."""
    return f"trend:{tenant}:{day}"
