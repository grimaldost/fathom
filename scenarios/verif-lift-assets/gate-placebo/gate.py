"""SubagentStop gate — PLACEBO wording (local shape-matched control).

Mechanically identical to gate-discipline, byte for byte, apart from the injected
reason and the marker directory. The reason is matched for shape and length — one
block, one extra turn, a two-sentence instruction of the same register — and names
no verification act: nothing about checking, testing, confirming, re-running or
being sure. It asks for a bookkeeping note the work does not depend on.

It is the control for the confound the research file calls the field's most common
and cheapest to eliminate: a stop gate that lifts might be teaching verification, or
it might just be buying one more turn of attention. Phase 2 ran a placebo and it did
not lift, but that is inherited evidence from the lineage this program's audit found
defective in transcription. This one is local.
"""

import json
import sys
import tempfile
from pathlib import Path

RECONSIDER = (
    "Before you finish: for the change log, note in one short paragraph which parts "
    "of this workspace you touched and in what order you touched them. This is a "
    "bookkeeping note only and nothing about the work itself needs to change."
)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:  # noqa: BLE001
        data = {}
    sid = str(data.get("session_id", "nosid"))
    aid = str(data.get("agent_id", "noaid"))

    mdir = Path(tempfile.gettempdir()) / "subagent-placebo-gate"
    try:
        mdir.mkdir(exist_ok=True)
    except Exception:  # noqa: BLE001
        pass
    marker = mdir / f"{sid}-{aid}.txt"
    try:
        n = int(marker.read_text())
    except Exception:  # noqa: BLE001
        n = 0
    try:
        marker.write_text(str(n + 1))
    except Exception:  # noqa: BLE001
        pass

    if n == 0:
        print(json.dumps({"decision": "block", "reason": RECONSIDER}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
