"""Driver for the convoy-gate arms: run convoy's standalone gate over a workspace.

Two callers, one script:

* **T-perPR** — the ORCHESTRATOR runs it after each PR::

      python <task_dir>/run_convoy_gate.py <task_dir> <workspace> --phase <pr phase> --json

  and hands a ``blocked`` envelope's repair text to a fix subagent.
* **T-final** — the HARNESS runs it once after the session, via the scenario's
  ``[gate].extra``::

      python "${task_dir}/run_convoy_gate.py" "${task_dir}" "${workspace}"

  with no ``--phase``, so the whole gate runs.

A gate spec's ``[[checks]].run`` strings are read by convoy, not by fathom, so they
cannot carry fathom placeholders and must be materialized with absolute paths per
trial. What this script does, in order:

1. Reads the five-PR decomposition's OWN ``[[checks]]`` out of ``series.toml`` — the
   same phase-scoped checks a governed run of that series would gate each PR on, so
   the T arms get no oracle content the decomposition did not already declare — and
   writes them to a per-trial TEMP gate spec (never the workspace, which is graded;
   never the task dir, which is shared read-only by parallel trials).
2. Appends the two blocking ``independent = true`` type-contract probes, whose
   ``asset`` is the probe's own task-dir path (out-of-tree from the workspace, so
   convoy's fail-closed isolation guard passes them): the arithmetic group from the
   phase that introduces booleans onward, the comparison group from the phase that
   introduces comparisons onward. Each carries a ``repair_hint`` restating the type
   rule the task statement gives (rule 4) — the rule only, never an implementation
   tip, so the hint carries nothing the control arm was not also told.
3. Invokes ``convoy gate <spec> -w <workspace> [--phase TAG ...] --json`` through the
   pinned release (``uvx --from git+...@<tag>``), so the measured artifact is the
   shipped surface.
4. Prints convoy's stderr narration and its JSON envelope through, and exits with
   convoy's own exit code (0 green / 1 blocking red / 3 usage).

Stdlib only. The probes MUST stay harness-side: they strengthen a gate, they are not
the acceptance oracle, and they must not reach an implementer's context.
"""

import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

# The pinned convoy release these arms measure. Part of the arm's identity: a convoy
# improvement lands as a new tag and therefore a NEW arm, never a silent mutation.
# 0.11.0 is the release carrying the envelope's `repair_brief` and `convoy_version`
# fields the T-perPR brief reads.
CONVOY_PIN = "git+https://github.com/grimaldost/convoy@v0.11.0"

# Arming-verification escape hatch: point the driver at a local convoy checkout so the
# whole path (spec materialization -> gate invocation -> exit propagation) can be proven
# to FIRE before any paid trial, and before the pinned tag exists. Never set during a
# measured run: the invocation actually used is echoed to stderr on every call, so a
# trial that ran under an override says so in its own ledger detail rather than being
# indistinguishable from a pinned one.
_OVERRIDE_ENV = "FATHOM_CONVOY_GATE_LOCAL"

_GATE_SPEC_ID = "multiagent-composition-gate"

# The phase each probe group becomes meaningful at. Both run from there to the end of
# the decomposition's declared phase order, which is read from series.toml rather than
# restated here, so a change to the decomposition cannot silently unscope a probe.
_ARITH_FROM = "bools"
_COMPARE_FROM = "compare"

# Verbatim from the task statement (task.toml, rule 4) and nothing more. An earlier draft
# added "bool is a subclass of int in Python, so excluding it takes an explicit check" —
# an implementation tip that appears nowhere in the task, i.e. information the treatment
# arms would have had and the control arm could not. Removed before any trial ran.
_ARITH_HINT = (
    "the task's stated type rule: arithmetic operators (+ - * / %) require numeric "
    "operands and reject booleans; a wrong-type operand raises TypeMismatchError, a new "
    "subclass of ExprError"
)
_COMPARE_HINT = (
    "the task's stated type rule: comparison operators (== != < <= > >=) require numeric "
    "operands and reject booleans; a wrong-type operand raises TypeMismatchError, a new "
    "subclass of ExprError"
)


def _toml_str(value: str) -> str:
    """A TOML basic string for *value* (backslash and quote escaped)."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _toml_list(values) -> str:
    return "[" + ", ".join(_toml_str(v) for v in values) + "]"


def _render_check(check: dict) -> str:
    """Render one gate check as a ``[[checks]]`` block."""
    lines = ["[[checks]]", f"name = {_toml_str(check['name'])}", f"run = {_toml_str(check['run'])}"]
    lines.append("blocking = " + ("true" if check.get("blocking", True) else "false"))
    lines.append("independent = " + ("true" if check.get("independent", False) else "false"))
    if check.get("phases"):
        lines.append(f"phases = {_toml_list(check['phases'])}")
    if check.get("asset"):
        lines.append(f"asset = {_toml_str(check['asset'])}")
    if check.get("repair_hint"):
        lines.append(f"repair_hint = {_toml_str(check['repair_hint'])}")
    return "\n".join(lines)


def _phase_order(series: dict) -> list[str]:
    """The decomposition's phase tags, in PR dependency order, deduplicated."""
    order: list[str] = []
    for pr in series.get("prs", []):
        phase = pr.get("phase")
        if phase and phase not in order:
            order.append(phase)
    return order


def _phases_from(order: list[str], first: str) -> list[str]:
    """``order`` from *first* to the end; empty when *first* is not declared."""
    return order[order.index(first) :] if first in order else []


def build_spec(series: dict, probe: str, workspace: str) -> str:
    """The gate spec text: the series' own checks plus the two independent probes.

    The probes take the workspace as an explicit absolute argument rather than
    relying on the check runner's cwd: the path a probe adds to ``sys.path`` is the
    one thing that must not be ambiguous.
    """
    order = _phase_order(series)
    arith = _phases_from(order, _ARITH_FROM)
    compare = _phases_from(order, _COMPARE_FROM)
    if not arith or not compare:
        raise ValueError(
            f"series.toml declares phases {order!r}; the probes need "
            f"{_ARITH_FROM!r} and {_COMPARE_FROM!r}"
        )
    blocks = [f"[series]\nid = {_toml_str(_GATE_SPEC_ID)}"]
    blocks += [_render_check(c) for c in series.get("checks", [])]
    blocks.append(
        _render_check(
            {
                "name": "type-contract-probe-arithmetic",
                "run": f'python "{probe}" "{workspace}" --group arith',
                "blocking": True,
                "independent": True,
                "phases": arith,
                "asset": probe,
                "repair_hint": _ARITH_HINT,
            }
        )
    )
    blocks.append(
        _render_check(
            {
                "name": "type-contract-probe-comparison",
                "run": f'python "{probe}" "{workspace}" --group compare',
                "blocking": True,
                "independent": True,
                "phases": compare,
                "asset": probe,
                "repair_hint": _COMPARE_HINT,
            }
        )
    )
    return "\n\n".join(blocks) + "\n"


def _parse_argv(argv):
    """Return (task_dir, workspace, phases) from the script's own ``argv[1:]``.

    ``--json`` is accepted and ignored: this driver always asks convoy for the JSON
    envelope, so the flag is there to keep the orchestrator brief's invocation literal
    rather than to switch anything.
    """
    phases: list[str] = []
    positional: list[str] = []
    rest = list(argv)
    while rest:
        arg = rest.pop(0)
        if arg == "--phase":
            if not rest:
                raise ValueError("--phase needs a tag")
            phases.append(rest.pop(0))
        elif arg.startswith("--phase="):
            phases.append(arg.split("=", 1)[1])
        elif arg == "--json":
            continue
        else:
            positional.append(arg)
    if len(positional) != 2:
        raise ValueError("usage: run_convoy_gate.py <task_dir> <workspace> [--phase TAG] [--json]")
    return positional[0], positional[1], phases


def main() -> int:
    # Force UTF-8 on our own streams before writing anything through. convoy's gate
    # narration contains em-dashes; on Windows this process's stdout/stderr default to
    # the console codepage (cp1252), which encodes U+2014 as the single byte 0x97 --
    # invalid UTF-8. The harness reads this process's output with encoding="utf-8"
    # (strict), so the reader thread raised UnicodeDecodeError and lost the captured
    # output for that call. The exit code survives, so gate verdicts were unaffected;
    # what is lost is the text a red gate's fix re-brief quotes.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    try:
        raw_task_dir, raw_workspace, phases = _parse_argv(sys.argv[1:])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    task_dir = Path(raw_task_dir).resolve()
    workspace = Path(raw_workspace).resolve()
    probe = (task_dir / "type_probe.py").resolve()
    series_file = task_dir / "series.toml"
    if not probe.is_file():
        print(f"arming failure: probe not found at {probe}", file=sys.stderr)
        return 3
    if not series_file.is_file():
        print(f"arming failure: series.toml not found at {series_file}", file=sys.stderr)
        return 3

    with series_file.open("rb") as fh:
        series = tomllib.load(fh)
    try:
        spec_text = build_spec(
            series,
            str(probe).replace("\\", "/"),
            str(workspace).replace("\\", "/"),
        )
    except ValueError as exc:
        print(f"arming failure: {exc}", file=sys.stderr)
        return 3

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
        phase_args = [a for tag in phases for a in ("--phase", tag)]
        proc = subprocess.run(
            [*launcher, "gate", str(spec_path), "-w", str(workspace), *phase_args, "--json"],
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
