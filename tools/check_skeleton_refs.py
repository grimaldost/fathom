"""Discrimination check for a bank: prove each task can separate a good answer from a plausible one.

`fathom validate` answers two questions — does the unmodified fixture leave something to do, and
is the verifier satisfiable at all. Neither catches the failure that has cost the most here: a task
where a *plausible but shallow* answer scores the same as a good one, so every arm ceilings and the
run returns a null the instrument manufactured. Both harder banks in this repo ceilinged that way,
after the spend rather than before it.

This tool checks the missing property, in the two shapes a task can take:

**Authoring tasks** ship ``refs/skeleton/`` — the spec a competent author produces from the section
headings alone, with no knowledge of the gate's parser. Required: the skeleton PASSES every
criterion in the shared class and FAILS at least one in the behaviour / note-only class. A skeleton
that passes everything means the task rewards structure only, and no amount of prose can move it.

**Repair tasks** ship a defective ``fixtures/spec.md`` instead. Required: the defect makes the
fixture fail at least one criterion OUTSIDE the shared class. A defect visible only in the shared
class is repaired by anyone who reads the document, and measures nothing about grounding.

Both shapes additionally require ``solution/`` to pass every criterion, not merely the exit gate:
a reference answer that leaves a criterion false is a criterion no arm can be expected to reach.

Free — local verifier runs only, no spawns. Usage::

    python tools/check_skeleton_refs.py keel-kit-ablation-v1
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SHARED = {
    "spec_written",
    "gate_part_a_passes",
    "numbered_sections_present",
    "manifest_is_bijection",
    "every_section_has_criterion",
    "no_placeholders",
    "kind_declared_single_change",
}
INTEGRITY = {
    "no_self_certification",
    "anchors_point_at_staged_files",
    "staged_tree_untouched",
    "defect_not_masked",
}


def score(task_dir: Path, overlay: str | None) -> dict[str, bool]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "ws"
        shutil.copytree(task_dir / "fixtures", root)
        if overlay is not None:
            shutil.copytree(task_dir / overlay, root, dirs_exist_ok=True)
        proc = subprocess.run(
            [sys.executable, str(task_dir / "verify.py"), str(root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        for line in reversed(proc.stdout.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
        raise SystemExit(f"{task_dir.name}: verifier emitted no criteria\n{proc.stderr[-1500:]}")


def check(bank: str) -> int:
    bank_dir = REPO / "tasks" / bank
    manifest = tomllib.loads((bank_dir / "bank.toml").read_text(encoding="utf-8"))
    failures: list[str] = []
    for task_dir in sorted(p for p in bank_dir.iterdir() if (p / "task.toml").exists()):
        name = task_dir.name
        shape = json.loads((task_dir / "profile.json").read_text(encoding="utf-8"))["shape"]
        seal = " [holdout]" if name in manifest.get("holdout", []) else ""

        solution = score(task_dir, "solution")
        unmet = sorted(k for k, v in solution.items() if not v)
        if unmet:
            failures.append(f"{name}: reference solution leaves {unmet} false")

        if shape == "authoring":
            skeleton_dir = task_dir / "refs" / "skeleton"
            if not skeleton_dir.is_dir():
                failures.append(f"{name}: authoring task ships no refs/skeleton/")
                continue
            skeleton = score(task_dir, "refs/skeleton")
            shared_gaps = sorted(k for k, v in skeleton.items() if k in SHARED and not v)
            discriminating = sorted(
                k for k, v in skeleton.items() if k not in SHARED and k not in INTEGRITY and not v
            )
            if shared_gaps and name != "author-single-change":
                failures.append(f"{name}: skeleton fails shared criteria {shared_gaps}")
            if not discriminating:
                failures.append(
                    f"{name}: skeleton passes every behaviour/note-only criterion — "
                    "the task cannot discriminate and must be re-authored"
                )
            print(f"  [ok] {name}{seal}: skeleton fails {discriminating}")
        else:
            fixture = score(task_dir, None)
            outside = sorted(
                k for k, v in fixture.items() if k not in SHARED and k not in INTEGRITY and not v
            )
            if not outside:
                failures.append(
                    f"{name}: the planted defect shows only in the shared class — "
                    "it measures document-reading, not grounding"
                )
            print(f"  [ok] {name}{seal}: defect shows outside the shared class in {outside}")

    print()
    if failures:
        for line in failures:
            print(f"FAIL {line}")
        print(f"\nDISCRIMINATION: {len(failures)} problem(s) — do not spend on this bank")
        return 1
    print("DISCRIMINATION: every task separates a shallow answer from a good one")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_skeleton_refs.py <bank>")
    raise SystemExit(check(sys.argv[1]))
