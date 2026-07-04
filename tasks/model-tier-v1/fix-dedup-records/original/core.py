"""Collapse duplicate person records."""


def dedupe(rows):
    """Return *rows* with duplicate people removed, keeping the first of each.

    Each row is a mapping with a ``"name"`` key. Two rows refer to the *same
    person* when their names match after normalization:

    * comparison is **case-insensitive** (``"Ada"`` == ``"ada"``), and
    * **leading and trailing whitespace is ignored** (``"  Ada "`` == ``"Ada"``).

    The **first** row seen for each person is the one kept (later duplicates are
    dropped), and the relative order of the kept rows matches their first
    appearance in *rows*. The kept rows are the original row objects, unmodified.
    """
    seen = set()
    out = []
    for row in rows:
        key = row["name"]
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out
