"""Phase-3 parameterized SubagentStop gate.

GATE_DISCIPLINE in {debug, data} x GATE_REGISTER in {discipline, prescriptive}
selects the injected reason. Within a discipline the two registers assert the SAME
substantive discipline; they differ only in whether they name an artifact to
produce. Phase 2 found (on verification) that the prescriptive register buys
footprint at a large false-positive cost while the discipline register does not;
this plugin tests whether that gap replicates on other disciplines.

Blocks each subagent once, guarded by a per-(session, agent) counter in the OS temp
dir, then lets the second stop through.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

WORDING = {
    ("debug", "discipline"): (
        "Before you finish: are you confident you addressed what actually causes "
        "this, or only the place where it showed up? Satisfy yourself that you "
        "understand the cause well enough to know everything it affects."
    ),
    ("debug", "prescriptive"): (
        "Before you finish: trace the fault back to the shared helper it comes from "
        "and patch it there rather than at the call site, then go through every "
        "caller of that helper and update each one. Do that now, then stop."
    ),
    ("data", "discipline"): (
        "Before you finish: have you actually looked at the output this produces "
        "against the real input, or are you trusting that the code reads correctly? "
        "Satisfy yourself that the numbers it puts out are the right numbers."
    ),
    ("data", "prescriptive"): (
        "Before you finish: run the pipeline end to end, print the resulting totals, "
        "and reconcile them line by line against the source rows to confirm every "
        "row is accounted for. Do that now, then stop."
    ),
}


def main() -> int:
    try:
        data = json.loads(sys.stdin.read())
    except Exception:  # noqa: BLE001
        data = {}
    discipline = os.environ.get("GATE_DISCIPLINE", "")
    register = os.environ.get("GATE_REGISTER", "")
    reason = WORDING.get((discipline, register))
    if reason is None:
        return 0  # unconfigured: behave as no gate at all

    sid = str(data.get("session_id", "nosid"))
    aid = str(data.get("agent_id", "noaid"))
    mdir = Path(tempfile.gettempdir()) / "subagent-gate-multi"
    try:
        mdir.mkdir(exist_ok=True)
    except Exception:  # noqa: BLE001
        pass
    marker = mdir / f"{discipline}-{register}-{sid}-{aid}.txt"
    try:
        n = int(marker.read_text())
    except Exception:  # noqa: BLE001
        n = 0
    try:
        marker.write_text(str(n + 1))
    except Exception:  # noqa: BLE001
        pass

    if n == 0:
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
