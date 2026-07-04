"""Clamp a value into an inclusive range."""


def clamp(x, lo, hi):
    """Constrain ``x`` to the inclusive range ``[lo, hi]``.

    Returns ``lo`` if ``x`` is below ``lo``, ``hi`` if ``x`` is above ``hi``,
    and ``x`` itself when it already lies within the range. Assumes
    ``lo <= hi``.
    """
    return lo if x < lo else x
