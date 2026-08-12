"""The reconciliation summary."""


def summarise(readings, pairs, gap_ids):
    """Return the counts a reconciliation run reports (S1)."""
    return {"readings": len(readings), "matched": len(pairs), "gaps": len(gap_ids)}
