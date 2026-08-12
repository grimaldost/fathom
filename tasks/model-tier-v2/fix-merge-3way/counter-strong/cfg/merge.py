"""Three-way merge of flat configuration maps.

COUNTER-SOLUTION FOR THE STRONG ORACLE, part 1 of 2 (harness-side, never staged).
The agreed-change branch is added to both entry points — copied, not shared — so
every criterion the standard oracle names is green. The deletion rule, which the
instruction never mentions, is still wrong in both copies: a deleted key comes back
holding the internal MISSING marker.
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
        if o == t:
            result[key] = o
        elif o == b:
            result[key] = t
        elif t == b:
            result[key] = o
        else:
            result[key] = Conflict(b, o, t)
    return result
