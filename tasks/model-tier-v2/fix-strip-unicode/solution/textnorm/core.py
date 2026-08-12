"""Normalise text for search keys and display labels."""

import unicodedata


def strip_accents(text):
    """Return *text* with accents removed and every other character preserved."""
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", without_marks)
