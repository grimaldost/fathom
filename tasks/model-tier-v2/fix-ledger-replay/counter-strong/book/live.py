"""Totals maintained incrementally, one event at a time.

COUNTER-SOLUTION FOR THE STRONG ORACLE (harness-side, never staged). The void branch
now remembers which ids it has already voided, so a repeated void is ignored and the
whole standard oracle is green. What it still assumes is that the post always arrived
first: a void for an id not yet posted is recorded and then forgotten, so when the
post turns up it is counted anyway. Only the strong oracle's out-of-order log and
prefix sweep look there.
"""


class LiveTotals:
    """Running totals for a process following the log."""

    def __init__(self):
        self.total = 0
        self.count = 0
        self._posted = {}
        self._voided = set()

    def apply(self, event):
        """Fold one event into the running totals."""
        if event["kind"] == "post":
            self._posted[event["id"]] = event["amount"]
            self.total += event["amount"]
            self.count += 1
        elif event["kind"] == "void" and event["id"] not in self._voided:
            self._voided.add(event["id"])
            if event["id"] in self._posted:
                self.total -= self._posted[event["id"]]
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
