"""Frozen external compatibility surface. DECOY: the public wrapper
keeps its historical name forever; only its internals may change."""
from ..core.compute import settle as _core


def settle(entries):
    """Historical name, kept for external callers."""
    return _core(entries)


def legacy_total(entries):
    """Historical helper used (for now) by internal modules."""
    return _core(entries)
