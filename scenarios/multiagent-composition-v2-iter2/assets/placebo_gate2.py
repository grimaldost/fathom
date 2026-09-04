"""Placebo gate in envelope form: the ceremony of a quality gate, carrying zero information.

The equal-content placebo of the iteration-2 pre-registration (arm placebo2 of
scenarios/multiagent-composition-v2-iter2). Iteration 1's placebo matched the convoy
gate's reds but not its repair actor -- perpr dispatched a fresh fix subagent with the
envelope's ``repair_brief``; the placebo brief repaired inside the orchestrator -- nor
the brief's content. Iteration 2 gives the placebo arm perpr2's brief byte for byte
except for the command it runs and the variable that names it, so the placebo has to
speak the driver's envelope: one JSON object on stdout with ``outcome`` and, on a red,
a ``repair_brief`` the orchestrator hands verbatim to a fresh fix subagent. The
repair brief names no check, no expression, no file, no type and no rule. placebo2
equals perpr2 in brief content and repair actor and differs only in what the gate
returns.

    python placebo_gate2.py <workspace> [--phase TAG] [--json]

``--phase`` and ``--json`` are accepted and ignored: they keep the brief's invocation
literal. Exit 1 with a ``blocked`` envelope on the first call for a given workspace,
exit 0 with a ``completed`` envelope afterwards. Same marker mechanism as
placebo_gate.py: a file under the OS temp dir named by a sha256 of the resolved
workspace path -- not in the workspace, which is graded, and not in the task dir,
which is shared read-only by parallel trials. Each trial gets a fresh workspace, so
each trial gets exactly one red.

The repair brief carries the literal phrase "transient check failed":
tools/stream_facts.py counts placebo reds by that marker. The same one-line message
goes to stderr, where the driver's narration goes.

Stdlib only.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

# Deliberately uninformative: the arm is the iteration, not the diagnosis. Names no
# check, no expression, no file, no type and no rule.
_REPAIR_BRIEF = (
    "quality gate: a transient check failed for this PR. Re-run the project's visible "
    "test suite from the project root, re-read the PR brief, and fix anything you find; "
    "then finish."
)
_OK_MESSAGE = "quality gate: ok"

_MARKER_PREFIX = "fathom-placebo-gate2-"


def marker_path(workspace: Path) -> Path:
    """The per-workspace marker file: OS temp dir, named by a hash of the path."""
    key = hashlib.sha256(str(Path(workspace).resolve()).encode("utf-8")).hexdigest()[:32]
    return Path(tempfile.gettempdir()) / f"{_MARKER_PREFIX}{key}"


def _parse_argv(argv) -> Path:
    """The workspace from ``argv``; ``--phase TAG`` / ``--phase=TAG`` / ``--json`` ignored."""
    positional = []
    rest = list(argv)
    while rest:
        arg = rest.pop(0)
        if arg == "--phase":
            if rest:
                rest.pop(0)
        elif arg.startswith("--phase=") or arg == "--json":
            continue
        else:
            positional.append(arg)
    return Path(positional[0]) if positional else Path(".")


def _emit(envelope: dict, message: str) -> None:
    print(json.dumps(envelope))
    print(message, file=sys.stderr)


def main(argv) -> int:
    # Force UTF-8 on both streams before writing anything: on Windows this process's
    # stdout defaults to the console codepage, which the harness then cannot decode as
    # UTF-8. Same hardening as the convoy-gate driver and placebo_gate.py.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    marker = marker_path(_parse_argv(argv))
    if marker.exists():
        _emit({"ok": True, "outcome": "completed"}, _OK_MESSAGE)
        return 0
    try:
        marker.write_text("1", encoding="utf-8")
    except OSError as exc:
        # A placebo that cannot record its own state would red every call and turn the
        # arm into an unbounded loop, so say so and green.
        _emit(
            {
                "ok": True,
                "outcome": "completed",
                "note": f"marker unwritable: {exc}",
            },
            f"{_OK_MESSAGE} (marker unwritable: {exc})",
        )
        return 0
    _emit(
        {"ok": False, "outcome": "blocked", "repair_brief": _REPAIR_BRIEF},
        _REPAIR_BRIEF,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
