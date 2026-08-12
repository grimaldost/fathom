"""Three-way merge of nested configuration maps."""

from cfg.merge import MISSING, Conflict


def merge_tree(base, ours, theirs):
    """Three-way merge that recurses into keys holding a map on all three sides."""
    result = {}
    for key in sorted(set(base) | set(ours) | set(theirs)):
        b = base.get(key, MISSING)
        o = ours.get(key, MISSING)
        t = theirs.get(key, MISSING)
        if isinstance(b, dict) and isinstance(o, dict) and isinstance(t, dict):
            result[key] = merge_tree(b, o, t)
        elif o == b:
            result[key] = t
        elif t == b:
            result[key] = o
        else:
            result[key] = Conflict(b, o, t)
    return result
