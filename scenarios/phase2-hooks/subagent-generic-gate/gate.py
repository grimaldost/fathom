"""SubagentStop gate — GENERIC wording (Phase-2 validity test).

Same mechanism and guard as subagent-verify-gate, but the injected reason states the
verification-before-completion discipline in its GENERAL form and deliberately avoids
every word tied to the measured criterion: no "check", no "test", no "regression", no
"add one now". If footprint still lifts under this wording, the +0.56 measured with
the specific gate is not merely teaching-to-the-test — the always-on gate mechanism
generalizes. If it collapses, the earlier result was criterion-naming, and a shipped
gate would need to name the behavior it wants.
"""

import json
import sys
import tempfile
from pathlib import Path

RECONSIDER = (
    "Before you finish: are you actually confident this is correct, or are you "
    "assuming it is? Take one more pass over what you changed and satisfy yourself "
    "that it genuinely works and that you would find out if it stopped working."
)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:  # noqa: BLE001
        data = {}
    sid = str(data.get("session_id", "nosid"))
    aid = str(data.get("agent_id", "noaid"))

    mdir = Path(tempfile.gettempdir()) / "subagent-generic-gate"
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
