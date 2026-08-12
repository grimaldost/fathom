"""Three-way merge of flat configuration maps."""

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


def resolve(b, o, t):
    """Apply the four documented rules to one key. ``MISSING`` means "drop it"."""
    if o == t:
        return o  # both sides agree — including both having deleted it
    if o == b:
        return t
    if t == b:
        return o
    return Conflict(b, o, t)


def merge(base, ours, theirs):
    """Three-way merge of two flat maps against their common *base*."""
    result = {}
    for key in sorted(set(base) | set(ours) | set(theirs)):
        value = resolve(base.get(key, MISSING), ours.get(key, MISSING), theirs.get(key, MISSING))
        if value is not MISSING and value != MISSING:
            result[key] = value
    return result
