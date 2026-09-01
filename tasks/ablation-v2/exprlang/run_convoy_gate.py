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

import subprocess
import sys
import tempfile
from pathlib import Path

# The pinned convoy release the arm measures. Part of the arm's identity: a convoy
# improvement lands as a new tag and therefore a NEW arm, never a silent mutation.
CONVOY_PIN = "git+https://github.com/grimaldost/convoy@v0.10.0"

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
    with tempfile.TemporaryDirectory(prefix="convoy-gate-") as tmp:
        spec_path = Path(tmp) / "gate-spec.toml"
        spec_path.write_text(spec_text, encoding="utf-8")
        proc = subprocess.run(
            [
                "uvx",
                "--from",
                CONVOY_PIN,
                "convoy",
                "gate",
                str(spec_path),
                "-w",
                str(workspace),
                "--json",
            ],
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
