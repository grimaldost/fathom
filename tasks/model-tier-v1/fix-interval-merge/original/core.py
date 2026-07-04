"""Merge overlapping or adjacent integer intervals."""


def merge(intervals):
    """Merge overlapping or adjacent intervals into a minimal disjoint set.

    Each interval is an inclusive integer ``(start, end)`` pair with
    ``start <= end``, and the input is given sorted by ``start``. Two intervals
    merge when they overlap **or touch**: touching means no integer lies strictly
    between them, i.e. the next start is at most one past the current end — so
    ``(1, 3)`` and ``(4, 6)`` merge into ``(1, 6)`` because 3 and 4 are
    consecutive. A merged interval runs from the earliest start to the **greatest**
    end among its members (a short interval contained in a longer one does not
    shorten it). Returns a new list of non-overlapping, non-adjacent ``(start,
    end)`` pairs in ascending order.
    """
    if not intervals:
        return []
    out = [tuple(intervals[0])]
    for start, end in intervals[1:]:
        last_start, last_end = out[-1]
        if start <= last_end:
            out[-1] = (last_start, end)
        else:
            out.append((start, end))
    return out
