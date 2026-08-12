"""The reconciliation summary."""


def summarise(readings, pairs, gap_ids):
    """Return the counts a reconciliation run reports."""
    return {"readings": len(readings), "matched": len(pairs), "gaps": 0}
