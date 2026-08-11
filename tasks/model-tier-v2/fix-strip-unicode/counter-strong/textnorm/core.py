"""Normalise text for search keys and display labels.

COUNTER-SOLUTION FOR THE STRONG ORACLE (harness-side, never staged). An explicit
fold table over the accented letters anyone would think to list. Every character
that is not in the table — including non-Latin scripts, currency and punctuation —
survives, so the whole standard oracle is green. What the table cannot do is handle
an accent it does not list, or an input written in decomposed form, where the
combining mark is a separate character the table never sees. Only the strong
oracle's independent checks reach that.
"""

_FOLD = str.maketrans(
    "áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝ",
    "aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNY",
)


def strip_accents(text):
    """Return *text* with accents removed and every other character preserved."""
    return text.translate(_FOLD)
