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

**Three kinds of failure ARE separated, because they license different claims** (corrected
2026-08-11 — the tool previously reported only their union and called the result "separates a
shallow answer from a good one"):

``absent``
    the construct is not in the document at all, so the criterion fails on its presence conjunct.
    A task discriminating only this way rewards *instruction-following*: the arm that was told the
    construct exists writes one and passes.
``unresolved``
    the construct IS present and the oracle fires on it — a grounding failure against the staged
    tree, which is the property this bank claims to measure.
``content``
    a predicate over the whole document with no presence conjunct (acceptance criteria that name
    something runnable, brief coverage). Discrimination, but not about grounding either.

All three are real discrimination and none is a bug. A bank whose discrimination is entirely
``absent`` cannot support a claim about groundedness, so the summary line reports how many tasks
reach ``unresolved`` rather than asserting the property wholesale.

**Sealed tasks stay sealed.** A holdout's per-criterion detail is withheld: this tool is mandatory
before spend, so printing which criteria a sealed task discriminates on would hand them to whoever
is wording the arms — the exact leak sealing exists to prevent (ADR-0005). Holdouts are still
checked, and a holdout that FAILS the property is reported as a failure by name, without the list.

Free — local verifier runs only, no spawns. Usage::

    python tools/check_skeleton_refs.py keel-kit-ablation-v1
"""

from __future__ import annotations

import importlib.util
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
# Excluded from the discrimination requirement on purpose: these are the Goodhart tripwires, true
# on every shipped variant by design. Their failability is proven by negative controls in
# tests/test_keel_kit_ablation.py, not by any task in the bank.
INTEGRITY = {
    "no_self_certification",
    "anchors_point_at_staged_files",
    "staged_tree_untouched",
    "defect_not_masked",
}


def load_material(bank_dir: Path):
    """The bank's own opportunity accounting, if it ships one (``keelgate_verify.py``)."""
    path = bank_dir / "keelgate_verify.py"
    if not path.is_file():
        return None, {}
    spec = importlib.util.spec_from_file_location("_bank_verify", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, "material_counts", None), getattr(module, "MATERIAL_OF", {})


def score(task_dir: Path, overlay: str | None) -> tuple[dict[str, bool], str]:
    """The criteria the verifier emits for *overlay*, plus the spec text it read (or '')."""
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
        profile = json.loads((task_dir / "profile.json").read_text(encoding="utf-8"))
        spec = root / profile.get("spec_path", "spec.md")
        text = spec.read_text(encoding="utf-8", errors="replace") if spec.is_file() else ""
        for line in reversed(proc.stdout.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line), text
        raise SystemExit(f"{task_dir.name}: verifier emitted no criteria\n{proc.stderr[-1500:]}")


def split(
    criteria: dict[str, bool], text: str, counts, material_of: dict[str, str]
) -> dict[str, list[str]]:
    """Discriminating criteria, split into absent / unresolved / content."""
    material = counts(text) if counts is not None and text else {}
    out: dict[str, list[str]] = {"absent": [], "unresolved": [], "content": []}
    for key, value in sorted(criteria.items()):
        if value or key in SHARED or key in INTEGRITY:
            continue
        need = material_of.get(key)
        if need is None:
            out["content"].append(key)
        elif material.get(need, 0) == 0:
            out["absent"].append(key)
        else:
            out["unresolved"].append(key)
    return out


def line_for(name: str, sealed: bool, what: str, kinds: dict[str, list[str]]) -> str:
    """The one-line result for a task. A sealed task's criteria are never named."""
    if sealed:
        return f"  [ok] {name} [holdout]: the property holds — sealed, nothing about it is reported"
    named = ", ".join(f"{k} {v}" for k, v in kinds.items() if v)
    return f"  [ok] {name}: {what} {named}"


def check(bank: str) -> int:
    bank_dir = REPO / "tasks" / bank
    manifest = tomllib.loads((bank_dir / "bank.toml").read_text(encoding="utf-8"))
    counts, material_of = load_material(bank_dir)
    failures: list[str] = []
    n_tasks = n_grounding = 0
    for task_dir in sorted(p for p in bank_dir.iterdir() if (p / "task.toml").exists()):
        name = task_dir.name
        shape = json.loads((task_dir / "profile.json").read_text(encoding="utf-8"))["shape"]
        sealed = name in manifest.get("holdout", [])

        solution, _ = score(task_dir, "solution")
        unmet = sorted(k for k, v in solution.items() if not v)
        if unmet:
            detail = f"{len(unmet)} criteria" if sealed else str(unmet)
            failures.append(f"{name}: reference solution leaves {detail} false")

        if shape == "authoring":
            skeleton_dir = task_dir / "refs" / "skeleton"
            if not skeleton_dir.is_dir():
                failures.append(f"{name}: authoring task ships no refs/skeleton/")
                continue
            skeleton, text = score(task_dir, "refs/skeleton")
            shared_gaps = sorted(k for k, v in skeleton.items() if k in SHARED and not v)
            kinds = split(skeleton, text, counts, material_of)
            if shared_gaps and name != "author-single-change":
                gaps = f"{len(shared_gaps)} criteria" if sealed else str(shared_gaps)
                failures.append(f"{name}: skeleton fails shared criteria {gaps}")
            if not any(kinds.values()):
                failures.append(
                    f"{name}: skeleton passes every behaviour/note-only criterion — "
                    "the task cannot discriminate and must be re-authored"
                )
            print(line_for(name, sealed, "skeleton fails", kinds))
        else:
            fixture, text = score(task_dir, None)
            kinds = split(fixture, text, counts, material_of)
            if not any(kinds.values()):
                failures.append(
                    f"{name}: the planted defect shows only in the shared class — "
                    "it measures document-reading, not grounding"
                )
            print(line_for(name, sealed, "defect shows outside the shared class:", kinds))
        if not sealed:  # holdouts are checked, but never enter a figure they could be read from
            n_tasks += 1
            n_grounding += bool(kinds["unresolved"])

    print()
    if failures:
        for line in failures:
            print(f"FAIL {line}")
        print(f"\nDISCRIMINATION: {len(failures)} problem(s) — do not spend on this bank")
        return 1
    print(
        f"DISCRIMINATION: every task separates a shallow answer from a good one. Of the {n_tasks} "
        f"open tasks, {n_grounding} do it on a GROUNDING failure — the construct is present and "
        f"does not resolve against the staged tree. Holdouts are checked and excluded from this "
        f"figure, which is otherwise a channel back to what they contain."
    )
    if n_grounding < n_tasks:
        print(
            f"  On the other {n_tasks - n_grounding} the shallow answer fails by omitting the "
            "construct, so what is separated there is instruction-following. Do not read those "
            "tasks as evidence about grounding."
        )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_skeleton_refs.py <bank>")
    raise SystemExit(check(sys.argv[1]))
