"""SubagentStop verification-before-completion gate (Phase-2 gated-sub arm).

Blocks each subagent ONCE (guarded by a per-(session,agent) counter in the OS temp
dir, so concurrent trials never collide and the block cannot loop) and injects a
verification-before-completion reconsideration. The injected reason reaches the
subagent (A2-confirmed) and forces it to continue. The second stop is allowed
through. This is the subagent analog of convoy's always-on gate: the discipline
runs as a stage, not a nudge the subagent has to self-select.
"""

import json
import sys
import tempfile
from pathlib import Path

RECONSIDER = (
    "Before you finish: prove the change actually works, and leave a check that "
    "would fail if it regressed. If you have not added a regression check that "
    "exercises the specific edge this change addresses, add one now, confirm it "
    "passes on your fixed code, then stop."
)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:  # noqa: BLE001
        data = {}
    sid = str(data.get("session_id", "nosid"))
    aid = str(data.get("agent_id", "noaid"))

    mdir = Path(tempfile.gettempdir()) / "subagent-verify-gate"
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
