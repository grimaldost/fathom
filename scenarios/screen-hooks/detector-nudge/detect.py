"""Lane-3 arm 5a+5b: fire a discipline nudge once, mid-trajectory, right before the
agent's first code edit, via PreToolUse additionalContext.

The target discipline is passed via DETECTOR_DISCIPLINE (set per-bank in the
scenario [env]); it selects the nudge text. The trigger is uniform: the first
Edit/Write to a non-test .py file (scratchpad paths ignored). PreToolUse is used
rather than PostToolUse because a failing test -- the emergent signal for the
debug case -- is a tool FAILURE, and PostToolUseFailure additionalContext does not
reach the model (measured 2026-07-24); intercepting the first code edit is the
reliable action-stream injection point.

Set DETNUDGE_TRACE to a file path to log each invocation (off in production).
"""

import json
import os
import sys
from pathlib import Path

NUDGES = {
    "systematic-debugging": (
        "Before you change the code here: if a defect is involved, trace it to its "
        "underlying cause and fix that -- and check whether the same cause reaches "
        "other call sites -- rather than patching the surface symptom."
    ),
    "data-engineering-discipline": (
        "Before you finalize this: verify the actual output values against "
        "realistic, messy input (blank, whitespace, or duplicate rows) rather than "
        "trusting the code path -- quiet miscounts hide in the edge rows."
    ),
    "verification-before-completion": (
        "Before you treat this as done: run the existing tests to confirm you "
        "haven't broken a behavior that already worked, and leave a check that "
        "would catch a regression."
    ),
}


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001
        return 0
    discipline = os.environ.get("DETECTOR_DISCIPLINE", "")
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    fp = str(tool_input.get("file_path", ""))
    name = Path(fp).name.lower()

    trace = os.environ.get("DETNUDGE_TRACE")
    if trace:
        try:
            with open(trace, "a", encoding="utf-8") as fh:
                fh.write(f"RAN disc={discipline!r} tool={tool_name!r} fp={fp!r}\n")
        except OSError:
            pass

    if discipline not in NUDGES:
        return 0
    if tool_name not in ("Edit", "Write"):
        return 0
    if not fp.endswith(".py") or "test" in name or "scratchpad" in fp.lower():
        return 0

    session = payload.get("session_id", "nosess")
    marker = Path(os.environ.get("TEMP", "/tmp")) / f"detnudge_{discipline}_{session}.fired"
    if marker.exists():
        return 0
    try:
        marker.write_text("1", encoding="utf-8")
    except OSError:
        pass

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": NUDGES[discipline],
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
