"""Verifier arming for verif-lift-v1: every criterion, proven satisfiable AND violable.

Run from the repo root (free -- no spawns, no spend)::

    uv run python tasks/verif-lift-v1/_authoring/arming.py

``fathom validate`` proves two points of the curve: the verifier fails on the
untouched fixture and passes on the reference solution.  That is necessary and not
sufficient.  It says nothing about the criteria that are *already true* on the
fixture -- ``scope_respected`` and ``proxy_instrument_ok`` -- so a bank can pass
validation while carrying a criterion that has never been observed false, which is
exactly the vacuous gate the measured skill exists to refuse.  A check seen only
green is indistinguishable from one that tests nothing.

So this walks each task through a set of counterexample workspaces built for the
purpose, runs the REAL ``verify.py`` against each, and requires the observed criteria
to match a declared expectation exactly.  A criterion is armed only when the corpus
of observations contains at least one True and at least one False for it.

The expectations are the interesting part; each row is a claim about the instrument:

``fixture``            nothing done: the work is outstanding, and nothing about the
                       instrument is broken.
``solution``           the reference fix WITH its regression check: every criterion
                       true, including a swap-back red that is an assertion failure.
``fix-no-check``       the same fix, no check left behind: the footprint criterion
                       goes false while correctness stays true.  This is the single
                       most important row -- it is the contrast the whole bank
                       measures, shown to be measurable before a dollar is spent.
``fix-vacuous-check``  a fix plus a check that exercises only the paths the defect
                       never touched.  The proxy must NOT be fooled by the presence
                       of a test file.
``signature-drift``    a fix that widens the signature, plus a check that uses the
                       new keyword.  The inverse edit makes that check ERROR rather
                       than fail; the instrument must score that as a vacuous red,
                       not as a caught regression.
``in-slice-only``      (TRUNC) the defect fixed inside the cited range only.
``edit-plus-checks``   (NULL) the trivial edit plus checks nobody asked for -- the
                       false-positive the program's veto is written against.
"""

from __future__ import annotations

import concurrent.futures
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS_DIR = HERE.parent

sys.path.insert(0, str(HERE))

from generate import CLASS_BANKS, STRONG_BANKS  # noqa: E402

T, F = True, False

# criterion -> expected value, per (class, overlay).  A criterion absent from a row
# is not emitted by that class.
EXPECTED: dict[tuple[str, str], dict[str, bool]] = {
    ("BUG", "fixture"): {"spec_met": F, "regression_check_present": F, "proxy_instrument_ok": T},
    ("BUG", "solution"): {"spec_met": T, "regression_check_present": T, "proxy_instrument_ok": T},
    ("BUG", "fix-no-check"): {
        "spec_met": T,
        "regression_check_present": F,
        "proxy_instrument_ok": T,
    },
    ("BUG", "fix-vacuous-check"): {
        "spec_met": T,
        "regression_check_present": F,
        "proxy_instrument_ok": T,
    },
    ("BUG", "signature-drift"): {
        "spec_met": T,
        "regression_check_present": F,
        "proxy_instrument_ok": F,
    },
    ("DATA", "fixture"): {
        "spec_met": F,
        "output_correct_on_subtle_case": F,
        "regression_check_present": F,
        "proxy_instrument_ok": T,
    },
    ("DATA", "solution"): {
        "spec_met": T,
        "output_correct_on_subtle_case": T,
        "regression_check_present": T,
        "proxy_instrument_ok": T,
    },
    ("DATA", "fix-no-check"): {
        "spec_met": T,
        "output_correct_on_subtle_case": T,
        "regression_check_present": F,
        "proxy_instrument_ok": T,
    },
    ("DATA", "fix-vacuous-check"): {
        "spec_met": T,
        "output_correct_on_subtle_case": T,
        "regression_check_present": F,
        "proxy_instrument_ok": T,
    },
    ("DATA", "signature-drift"): {
        "spec_met": T,
        "output_correct_on_subtle_case": T,
        "regression_check_present": F,
        "proxy_instrument_ok": F,
    },
    ("TRUNC", "fixture"): {"spec_met": F, "defect_past_slice_handled": F},
    ("TRUNC", "solution"): {"spec_met": T, "defect_past_slice_handled": T},
    ("TRUNC", "in-slice-only"): {"spec_met": T, "defect_past_slice_handled": F},
    ("NULL", "fixture"): {"spec_met": F, "scope_respected": T},
    ("NULL", "solution"): {"spec_met": T, "scope_respected": T},
    ("NULL", "edit-plus-checks"): {"spec_met": T, "scope_respected": F},
}

OVERLAYS: dict[str, list[str]] = {
    "BUG": ["fixture", "solution", "fix-no-check", "fix-vacuous-check", "signature-drift"],
    "DATA": ["fixture", "solution", "fix-no-check", "fix-vacuous-check", "signature-drift"],
    "TRUNC": ["fixture", "solution", "in-slice-only"],
    "NULL": ["fixture", "solution", "edit-plus-checks"],
}


def _overlay_dir(task_dir: Path, overlay: str) -> Path | None:
    if overlay == "fixture":
        return None
    if overlay == "solution":
        return task_dir / "solution"
    return task_dir / "refs" / overlay


def run_one(task_dir: Path, overlay: str) -> dict:
    """Build the workspace, run the real verify.py, return the emitted criteria."""
    tmp = tempfile.mkdtemp(prefix="vlift-arm-")
    try:
        work = Path(tmp) / "view"
        shutil.copytree(task_dir / "fixtures", work)
        source = _overlay_dir(task_dir, overlay)
        if source is not None:
            if not source.is_dir():
                return {"__error__": f"missing overlay {overlay}"}
            shutil.copytree(source, work, dirs_exist_ok=True)
        proc = subprocess.run(
            [sys.executable, str(task_dir / "verify.py"), str(work)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        try:
            return json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception:
            return {"__error__": f"non-JSON stdout: {proc.stdout[-300:]} / {proc.stderr[-300:]}"}
    except Exception as exc:  # noqa: BLE001
        return {"__error__": f"{type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _strong_equivalence() -> list[str]:
    """The strong banks carry no ``refs/``; they must be byte-identical instead.

    Arming proves the instrument on the weak bank's copy of a task.  The strong bank
    reuses that task, so the proof transfers only while the bytes match -- which is
    a claim, and therefore gets checked rather than assumed.
    """
    problems: list[str] = []
    for cls, strong_name in STRONG_BANKS.items():
        weak = TASKS_DIR / CLASS_BANKS[cls]
        strong = TASKS_DIR / strong_name
        for task_dir in sorted(strong.iterdir()):
            if not (task_dir / "spec.json").is_file():
                continue
            for path in sorted(task_dir.rglob("*")):
                if not path.is_file():
                    continue
                twin = weak / task_dir.name / path.relative_to(task_dir)
                if not twin.is_file() or twin.read_bytes() != path.read_bytes():
                    problems.append(f"{strong_name}/{task_dir.name}/{path.name} differs from weak")
    return problems


def main() -> int:
    tasks = []
    for bank_name in CLASS_BANKS.values():
        for task_dir in sorted((TASKS_DIR / bank_name).iterdir()):
            if not (task_dir / "spec.json").is_file():
                continue
            spec = json.loads((task_dir / "spec.json").read_text(encoding="utf-8"))
            tasks.append((task_dir, spec["class"]))

    jobs = [(task_dir, cls, ov) for task_dir, cls in tasks for ov in OVERLAYS[cls]]
    print(f"arming {len(tasks)} tasks over {len(jobs)} counterexample workspaces...")

    results: dict[tuple[str, str], dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(run_one, task_dir, ov): (task_dir.name, cls, ov)
            for task_dir, cls, ov in jobs
        }
        done = 0
        for future in concurrent.futures.as_completed(futures):
            name, cls, ov = futures[future]
            results[(name, ov)] = future.result()
            done += 1
            if done % 40 == 0:
                print(f"  {done}/{len(jobs)}")

    mismatches: list[str] = []
    # criterion -> {"true": n, "false": n}
    seen: dict[str, dict[str, int]] = {}
    per_task_armed: dict[str, bool] = {}

    for task_dir, cls in tasks:
        name = task_dir.name
        task_seen: dict[str, set] = {}
        for ov in OVERLAYS[cls]:
            observed = results[(name, ov)]
            if "__error__" in observed:
                mismatches.append(f"{name}/{ov}: verifier error: {observed['__error__']}")
                continue
            expected = EXPECTED[(cls, ov)]
            for criterion, want in expected.items():
                got = observed.get(criterion)
                if got is not want:
                    mismatches.append(
                        f"{name}/{ov}: {criterion} = {got!r}, expected {want!r} (full: {observed})"
                    )
                bucket = seen.setdefault(criterion, {"true": 0, "false": 0})
                bucket["true" if got else "false"] += 1
                task_seen.setdefault(criterion, set()).add(bool(got))
        per_task_armed[name] = all(len(values) == 2 for values in task_seen.values()) and bool(
            task_seen
        )

    print("\nCriterion coverage across the corpus (satisfiable AND violable):")
    unarmed = []
    for criterion in sorted(seen):
        counts = seen[criterion]
        armed = counts["true"] > 0 and counts["false"] > 0
        print(
            f"  [{'ARMED' if armed else 'NOT ARMED'}] {criterion}: "
            f"{counts['true']} observed true, {counts['false']} observed false"
        )
        if not armed:
            unarmed.append(criterion)

    weak = [name for name, armed in per_task_armed.items() if not armed]
    print(
        f"\nPer-task: {len(per_task_armed) - len(weak)}/{len(per_task_armed)} tasks show every "
        f"criterion they emit both true and false on their own workspaces."
    )
    if weak:
        print(f"  tasks whose criteria are not individually two-sided: {weak}")

    drift = _strong_equivalence()
    print(
        f"Strong-tier banks: {'byte-identical to their armed weak twins' if not drift else drift}"
    )
    mismatches.extend(drift)

    if mismatches:
        print(f"\n{len(mismatches)} EXPECTATION MISMATCHES:", file=sys.stderr)
        for line in mismatches[:60]:
            print("  -", line, file=sys.stderr)
        if len(mismatches) > 60:
            print(f"  ... and {len(mismatches) - 60} more", file=sys.stderr)

    ok = not mismatches and not unarmed and not weak
    print("\nVERIFIER ARMING:", "ALL CRITERIA ARMED" if ok else "NOT ARMED — DO NOT SPEND")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
