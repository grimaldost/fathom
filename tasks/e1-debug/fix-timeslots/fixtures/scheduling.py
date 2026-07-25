"""Slot math for the booking calendar."""


def slots_needed(total_minutes, slot_len):
    """How many slots are needed to cover `total_minutes`, `slot_len` each."""
    return total_minutes // slot_len


def slot_labels(total_minutes, slot_len):
    """The list of slot numbers the booking strip should offer, e.g. 65 minutes
    at 30 per slot -> [1, 2, 3]. Rendered as the clickable slots in the UI.
    """
    return list(range(1, slots_needed(total_minutes, slot_len) + 1))


def is_bookable(total_minutes, slot_len, n):
    """Whether slot number `n` exists for this window. Used to validate an
    incoming '?slot=N' reservation request before the slot is booked.
    """
    return 1 <= n <= slots_needed(total_minutes, slot_len)
