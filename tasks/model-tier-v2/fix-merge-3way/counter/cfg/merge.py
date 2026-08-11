"""Three-way merge of flat configuration maps.

COUNTER-SOLUTION (harness-side, never staged). One branch added to `merge` for the
case the instruction reports. `nested.merge_tree` carries its own copy of the rules
and still calls the agreed change a conflict. Satisfies the thin oracle; caught by
the standard oracle.
"""

MISSING = "<missing>"


class Conflict:
    """Both sides changed a key, to different values."""

    def __init__(self, base, ours, theirs):
        self.base = base
        self.ours = ours
        self.theirs = theirs

    def __eq__(self, other):
        return (
            isinstance(other, Conflict)
            and self.base == other.base
            and self.ours == other.ours
            and self.theirs == other.theirs
        )

    def __hash__(self):
        return hash((self.base, self.ours, self.theirs))

    def __repr__(self):
        return f"Conflict({self.base!r}, {self.ours!r}, {self.theirs!r})"


def merge(base, ours, theirs):
    """Three-way merge of two flat maps against their common *base*."""
    result = {}
    for key in sorted(set(base) | set(ours) | set(theirs)):
        b = base.get(key, MISSING)
        o = ours.get(key, MISSING)
        t = theirs.get(key, MISSING)
        if o == b:
            result[key] = t
        elif t == b:
            result[key] = o
        elif o == t:
            result[key] = o
        else:
            result[key] = Conflict(b, o, t)
    return result
