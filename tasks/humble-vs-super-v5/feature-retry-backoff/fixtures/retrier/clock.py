"""Small time helpers for retrier."""

import time


def elapsed(start, monotonic=time.monotonic):
    """Seconds elapsed since ``start`` (a prior ``monotonic()`` reading)."""
    return monotonic() - start
