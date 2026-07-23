"""Split a money amount fairly among recipients."""


def split_amount(total_cents, n):
    """Divide *total_cents* among *n* recipients as evenly as possible.

    Returns a list of *n* non-negative integer cent amounts that sum **exactly** to
    *total_cents*. When the total does not divide evenly, the leftover cents are
    handed out one each to the **earliest** recipients, so every two shares differ
    by at most one cent and the larger shares come first. For example
    ``split_amount(90, 3)`` is ``[30, 30, 30]``. *n* must be positive; *total_cents*
    must be non-negative.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if total_cents < 0:
        raise ValueError("total_cents must be non-negative")
    base = total_cents // n
    return [base] * n
