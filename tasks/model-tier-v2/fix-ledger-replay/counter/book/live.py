"""Totals maintained incrementally, one event at a time.

COUNTER-SOLUTION (harness-side, never staged). The report is that the count is one
too high after a void, so the void branch decrements the count. The log in the
instruction now matches; a log where the same id is voided twice subtracts twice.
Satisfies the thin oracle; caught by the standard oracle.
"""


class LiveTotals:
    """Running totals for a process following the log."""

    def __init__(self):
        self.total = 0
        self.count = 0
        self._posted = {}

    def apply(self, event):
        """Fold one event into the running totals."""
        if event["kind"] == "post":
            self._posted[event["id"]] = event["amount"]
            self.total += event["amount"]
            self.count += 1
        elif event["kind"] == "void":
            self.total -= self._posted.get(event["id"], 0)
            self.count -= 1

    def snapshot(self):
        """The totals as they stand."""
        return {"total": self.total, "count": self.count}


def fold(events):
    """Apply every event in order and return the resulting totals."""
    totals = LiveTotals()
    for event in events:
        totals.apply(event)
    return totals.snapshot()
