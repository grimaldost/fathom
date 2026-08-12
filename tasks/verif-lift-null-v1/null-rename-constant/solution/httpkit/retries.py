"""Retry policy constants and helpers."""

MAX_ATTEMPTS = 5
BACKOFF_BASE_S = 0.5


def attempts_left(used: int) -> int:
    """How many attempts remain after *used* have been spent."""
    return max(MAX_ATTEMPTS - used, 0)


def backoff_for(attempt: int) -> float:
    """Seconds to wait before *attempt*, doubling each time."""
    return BACKOFF_BASE_S * (2 ** max(attempt - 1, 0))
