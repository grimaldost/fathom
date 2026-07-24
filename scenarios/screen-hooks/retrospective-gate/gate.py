"""Lane-3 arm 5e: retrospective end-of-turn gate.

On the FIRST Stop of a turn, block once (decision:block) and feed back a
discipline reconsideration prompt selected by GATE_DISCIPLINE (set per-bank in the
scenario [env]). A session-keyed marker and the payload's `stop_hook_active` flag
both guard against re-blocking, so the agent is forced to reconsider exactly once
and can then finish.

Set GATE_TRACE to a file path to log each Stop invocation (off in production).
"""

import json
import os
import sys
from pathlib import Path

CHECKS = {
    "systematic-debugging": (
        "Before you finish: did this task involve a defect with an underlying "
        "cause? If you patched a surface symptom, go back, fix the root cause, and "
        "check whether the same cause reaches other call sites. Then finish."
    ),
    "data-engineering-discipline": (
        "Before you finish: did you verify the actual output values against "
        "realistic, messy input (blank, whitespace, or duplicate rows)? If not, "
        "check them now and correct any quiet miscount. Then finish."
    ),
    "verification-before-completion": (
        "Before you finish: did you run the existing tests to confirm no "
        "pre-existing behavior broke, and leave a check that would catch a "
        "regression? If not, do so now. Then finish."
    ),
}


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001
        return 0
    discipline = os.environ.get("GATE_DISCIPLINE", "")
    stop_active = payload.get("stop_hook_active")

    trace = os.environ.get("GATE_TRACE")
    if trace:
        try:
            with open(trace, "a", encoding="utf-8") as fh:
                fh.write(f"STOP disc={discipline!r} stop_hook_active={stop_active!r}\n")
        except OSError:
            pass

    if discipline not in CHECKS:
        return 0
    if stop_active:
        return 0
    session = payload.get("session_id", "nosess")
    marker = Path(os.environ.get("TEMP", "/tmp")) / f"retrogate_{discipline}_{session}.fired"
    if marker.exists():
        return 0
    try:
        marker.write_text("1", encoding="utf-8")
    except OSError:
        pass

    print(json.dumps({"decision": "block", "reason": CHECKS[discipline]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
