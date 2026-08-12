"""Totals recomputed from the whole log."""


def replay(events):
    """Recompute the totals from the entire event log."""
    voided = {e["id"] for e in events if e["kind"] == "void"}
    posts = [e for e in events if e["kind"] == "post" and e["id"] not in voided]
    return {"total": sum(e["amount"] for e in posts), "count": len(posts)}
