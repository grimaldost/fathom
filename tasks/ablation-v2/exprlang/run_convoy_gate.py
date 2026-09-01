"""Driver for arm A3 (`haiku-convoy-gate`): run convoy's standalone gate over the trial.

Invoked by the scenario's ``[gate].extra`` as
``python "${task_dir}/run_convoy_gate.py" "${task_dir}" "${workspace}"`` — fathom
substitutes the two placeholders at run time, and this script bridges them into
convoy's world: a gate spec's ``[[checks]].run`` strings are read by convoy, not by
fathom, so they cannot carry fathom placeholders and must be materialized with
absolute paths per trial.

What it does, in order:

1. Writes a minimal convoy gate spec to a per-trial TEMP file (never the workspace —
   the tree being graded must not grow harness files; never the task dir — it is
   shared by parallel trials and stays read-only): the task's visible suite as a
   blocking check, plus ``type_probe.py`` as a blocking ``independent = true`` check
   whose ``asset`` is the probe's own task-dir path (out-of-tree from the workspace,
   so convoy's fail-closed isolation guard passes it).
2. Invokes ``convoy gate <spec> -w <workspace> --json`` through the pinned release
   (``uvx --from git+...@<tag>``), so the measured artifact is the shipped surface.
3. Prints convoy's stderr narration and JSON envelope through (the fix loop re-briefs
   on this output), and exits with convoy's own exit code (0 green / 1 blocking red /
   3 usage) — gated-session treats nonzero as a red gate.

Stdlib only. The probe MUST stay harness-side: it strengthens the gate; it is not the
acceptance oracle and must not reach the implementer's context.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# The pinned convoy release the arm measures. Part of the arm's identity: a convoy
# improvement lands as a new tag and therefore a NEW arm, never a silent mutation.
CONVOY_PIN = "git+https://github.com/grimaldost/convoy@v0.10.0"

# Arming-verification escape hatch: point the driver at a local convoy checkout so the
# whole path (spec materialization -> gate invocation -> exit propagation) can be proven
# to FIRE before any paid trial, and before the pinned tag exists. Never set during a
# measured run: the invocation actually used is echoed to stderr on every call, so a
# trial that ran under an override says so in its own ledger detail rather than being
# indistinguishable from a pinned one. This is the sg2 lesson mechanized — that arm's
# probe never executed and nothing said so until the spend was gone.
_OVERRIDE_ENV = "FATHOM_CONVOY_GATE_LOCAL"

_SPEC_TEMPLATE = """\
[series]
id = "gate-composition-a3"

[[checks]]
name = "visible-suite"
run = "python -m unittest discover -s tests -t ."
blocking = true
independent = false

[[checks]]
name = "type-contract-probe"
run = "python \\"{probe}\\" \\"{workspace}\\""
blocking = true
independent = true
asset = "{probe}"
repair_hint = "the task statement's own type rules: arithmetic and comparison operators reject boolean operands; and/or/not reject numbers; the error is an ExprError subclass"
"""


def main() -> int:
    # Force UTF-8 on our own streams before writing anything through. convoy's gate
    # narration contains em-dashes; on Windows this process's stdout/stderr default to
    # the console codepage (cp1252), which encodes U+2014 as the single byte 0x97 --
    # invalid UTF-8. The harness reads this process's output with encoding="utf-8"
    # (strict), so the reader thread raised UnicodeDecodeError and lost the captured
    # output for that call. The exit code survives, so gate verdicts were unaffected;
    # what is lost is the text a red gate's fix re-brief quotes. Same posture as the
    # engine's own stream hardening.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) != 3:
        print("usage: run_convoy_gate.py <task_dir> <workspace>", file=sys.stderr)
        return 3
    task_dir = Path(sys.argv[1]).resolve()
    workspace = Path(sys.argv[2]).resolve()
    probe = (task_dir / "type_probe.py").resolve()
    if not probe.is_file():
        print(f"arming failure: probe not found at {probe}", file=sys.stderr)
        return 3

    spec_text = _SPEC_TEMPLATE.format(
        probe=str(probe).replace("\\", "/"),
        workspace=str(workspace).replace("\\", "/"),
    )
    local = os.environ.get(_OVERRIDE_ENV, "").strip()
    with tempfile.TemporaryDirectory(prefix="convoy-gate-") as tmp:
        spec_path = Path(tmp) / "gate-spec.toml"
        spec_path.write_text(spec_text, encoding="utf-8")
        if local:
            launcher = ["uv", "run", "--project", local, "convoy"]
            provenance = f"LOCAL CHECKOUT {local} (arming verification, not a measured run)"
        else:
            launcher = ["uvx", "--from", CONVOY_PIN, "convoy"]
            provenance = CONVOY_PIN
        # Echoed on every call so the arm's ledger detail records WHICH convoy ran.
        print(f"convoy gate via: {provenance}", file=sys.stderr)
        proc = subprocess.run(
            [*launcher, "gate", str(spec_path), "-w", str(workspace), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    # Pass both streams through: the JSON envelope on stdout is the record, the stderr
    # narration is what a fix re-brief quotes.
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
