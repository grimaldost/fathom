"""Placebo gate: the ceremony of a quality gate, carrying zero information.

The control for the arm P of the multiagent-composition pre-registration. If the
convoy-gate arms beat the control, the gain could be the gate's INDEPENDENT
information or merely the extra round of verify-and-fix the gate's red forces. This
script supplies the extra round and nothing else: it reds exactly once per workspace,
with a message that names no check, no expression, no file and no rule, then greens
for every later call.

    python placebo_gate.py <workspace>

Exit 1 on the first call for a given workspace, exit 0 afterwards. The marker is a
file under the OS temp dir named by a sha256 of the resolved workspace path -- not a
file in the workspace, because the tree being graded must not grow harness files, and
not a file in the task dir, which is shared read-only by parallel trials. Each trial
gets a fresh workspace, so each trial gets exactly one red.

Stdlib only.
"""

import hashlib
import sys
import tempfile
from pathlib import Path

# Deliberately uninformative: the arm is the iteration, not the diagnosis.
_MESSAGE = "quality gate: a transient check failed — re-run your verification and fix any issue"

_MARKER_PREFIX = "fathom-placebo-gate-"


def marker_path(workspace: Path) -> Path:
    """The per-workspace marker file: OS temp dir, named by a hash of the path."""
    key = hashlib.sha256(str(Path(workspace).resolve()).encode("utf-8")).hexdigest()[:32]
    return Path(tempfile.gettempdir()) / f"{_MARKER_PREFIX}{key}"


def main(argv) -> int:
    # The message carries an em-dash; on Windows this process's stdout defaults to the
    # console codepage, which the harness then cannot decode as UTF-8. Same hardening
    # as the convoy-gate driver.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    workspace = Path(argv[0]) if argv else Path(".")
    marker = marker_path(workspace)
    if marker.exists():
        print("quality gate: ok")
        return 0
    try:
        marker.write_text("1", encoding="utf-8")
    except OSError as exc:
        # Fail closed the same way a real gate would rather than silently greening:
        # a placebo that cannot record its own state would red every call and turn
        # the arm into an unbounded loop, so say so and green.
        print(f"quality gate: ok (marker unwritable: {exc})")
        return 0
    print(_MESSAGE)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
