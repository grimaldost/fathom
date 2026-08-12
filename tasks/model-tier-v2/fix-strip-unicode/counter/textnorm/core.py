"""Normalise text for search keys and display labels.

COUNTER-SOLUTION (harness-side, never staged). The canonical shortcut for the
reported words: decompose, then drop everything that will not survive ASCII. The two
words in the instruction come out right, and every non-Latin character is still
deleted — the original bug, untouched. Satisfies the thin oracle; caught by the
standard oracle.
"""

import unicodedata


def strip_accents(text):
    """Return *text* with accents removed and every other character preserved."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
