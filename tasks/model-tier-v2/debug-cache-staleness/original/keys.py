"""Cache keys for the feed views."""


def summary_key(tenant: str) -> str:
    """Key for the summary view."""
    return f"summary:{tenant}"


def report_key(tenant: str) -> str:
    """Key for the daily report view."""
    return f"report:{tenant}"


def trend_key(tenant: str) -> str:
    """Key for the trend view."""
    return f"trend:{tenant}"
