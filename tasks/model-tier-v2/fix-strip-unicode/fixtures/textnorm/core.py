"""Normalise text for search keys and display labels."""


def strip_accents(text):
    """Return *text* with accents removed and every other character preserved."""
    return text.encode("ascii", "ignore").decode("ascii")
