"""The deployment's local clock, as a fixed rule set."""

from datetime import date

# One hour ahead of standard time over this closed range, standard time otherwise.
# The change happens at local midnight.
_AHEAD_FROM = date(2026, 3, 9)
_AHEAD_THROUGH = date(2026, 11, 1)

STANDARD_OFFSET_MINUTES = -300
AHEAD_OFFSET_MINUTES = -240


def offset_minutes(local_day):
    """UTC offset in minutes in force from local midnight of *local_day*."""
    if _AHEAD_FROM <= local_day <= _AHEAD_THROUGH:
        return AHEAD_OFFSET_MINUTES
    return STANDARD_OFFSET_MINUTES
