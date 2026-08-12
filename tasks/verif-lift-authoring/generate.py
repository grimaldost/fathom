"""Materialise the verif-lift banks from the spec tables, proving as it goes.

Run from the repo root::

    uv run python tasks/verif-lift-authoring/generate.py

Emits one bank per task class plus the two strong-tier subsample banks; see
``README.md`` beside this file for why the classes are separate banks.

Nothing is written until every authored property has been checked against real code:

* base cases PASS on the buggy source (so the shipped suite cannot manufacture a red)
* edge cases FAIL on the buggy source and PASS on the fixed source (so ``spec_met``
  is both violable and satisfiable)
* subtle cases FAIL on the buggy source and PASS on the fixed source (same, for the
  DATA co-primary)
* for TRUNC, the past-slice twin FAILS on the buggy source and PASSES on the fixed
  one, and the cited line range ends BEFORE the twin's ``def`` line in the file that
  actually ships
* the shipped suite is green on the untouched fixture (the task gate)

The verifier-level proof -- every criterion demonstrated true on one overlay and
false on another, on real verifier runs -- lives in ``arming.py`` and runs after
this.  Together they are the seen-red evidence the bank owes before any spend.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS_DIR = HERE.parent
DATASET_VERSION = "1"

# One bank per class.  The classes carry different criteria and, per the plan,
# different arms -- the placebo arm rides only on the code class and the null bank --
# and fathom runs one scenario matrix per bank, so a single bank would force every
# arm onto every class and buy trials the plan did not budget.
CLASS_BANKS = {
    "BUG": "verif-lift-bug-v1",
    "DATA": "verif-lift-data-v1",
    "TRUNC": "verif-lift-trunc-v1",
    "NULL": "verif-lift-null-v1",
}

# The strong tier runs three arms over a PRE-DECLARED subsample, fixed here before
# any trial: the first 12 non-holdout tasks of the class in spec-table order.  It is
# a separate bank because fathom selects tasks by bank, not by flag.  Task content is
# copied verbatim from the weak bank and asserted byte-identical, so the tier x arm
# interaction is computed on the same tasks at both tiers.
STRONG_BANKS = {"BUG": "verif-lift-bug-strong-v1", "DATA": "verif-lift-data-strong-v1"}
STRONG_K = 12

sys.path.insert(0, str(HERE))

from spec_bug import BUG  # noqa: E402
from spec_data import DATA  # noqa: E402
from spec_null import NULL  # noqa: E402
from spec_trunc import TRUNC  # noqa: E402

# The sealed holdout (ADR-0005): excluded from every run unless --include-holdout.
# One task per class per lane, chosen before any trial and never screened.
HOLDOUT = [
    "bug-ordinal",
    "bug-column-width",
    "data-reconcile",
    "data-rolling-max",
    "trunc-abbrev",
    "null-log-wording",
]

GATE_CMD = "python -m unittest discover -s tests -t . -q"

CLASS_OF = {cls: cls for cls in CLASS_BANKS}


def bank_dir(cls: str) -> Path:
    return TASKS_DIR / CLASS_BANKS[cls]


VERIFY_SHIM = '''"""Acceptance verifier for {task_id} (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result view).  All logic lives
in the bank's shared ``_lib/proxy.py`` so every task in a class is scored by the same
instrument; the per-task detail is the declarative ``spec.json`` beside this file.
Both are task-constant -- identical for every arm -- so reading them leaks no
scenario identity (ADR-0003).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_lib"))

import proxy  # noqa: E402

if __name__ == "__main__":
    sys.exit(proxy.main(Path(__file__).resolve().parent, sys.argv))
'''

BASE_TEST_HEADER = '''"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from {dotted} import {func}


class ShippedChecks(unittest.TestCase):
'''

SOLUTION_TEST_HEADER = '''"""Regression checks added with the fix."""

import unittest

from {dotted} import {func}


class RegressionChecks(unittest.TestCase):
'''


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _case_body(func: str, cases: list, indent: str = "        ") -> str:
    lines = []
    for index, (args, expected) in enumerate(cases):
        call = f"{func}({', '.join(repr(a) for a in args)})"
        if isinstance(expected, dict) and "raises" in expected:
            lines.append(f"{indent}with self.assertRaises({expected['raises']}):")
            lines.append(f"{indent}    {call}")
        else:
            lines.append(f"{indent}self.assertEqual({call}, {expected!r})")
        if index != len(cases) - 1:
            lines.append("")
    return "\n".join(lines)


def _render_tests(header: str, dotted: str, funcs: list, blocks: list) -> str:
    body = header.format(dotted=dotted, func=", ".join(funcs))
    parts = [body]
    for name, cases, func in blocks:
        parts.append(f"    def test_{name}(self):\n{_case_body(func, cases)}\n")
    parts.append('\nif __name__ == "__main__":\n    unittest.main()\n')
    return "\n".join(parts)


def _load_from_source(source: str, name: str):
    """Import *source* as a throwaway module and return it."""
    tmp = tempfile.mkdtemp(prefix="vlift-check-")
    try:
        path = Path(tmp) / f"{name}.py"
        path.write_text(source, encoding="utf-8")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _cases_pass(source: str, func: str, cases: list, tag: str) -> bool:
    module = _load_from_source(source, f"probe_{tag}")
    fn = getattr(module, func)
    for args, expected in cases:
        wants_raise = isinstance(expected, dict) and "raises" in expected
        try:
            got = fn(*args)
        except Exception as exc:  # noqa: BLE001
            if wants_raise and type(exc).__name__ == expected["raises"]:
                continue
            return False
        if wants_raise:
            return False
        if got != expected:
            return False
    return True


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"BANK AUTHORING ERROR: {message}")


def _def_line(source: str, func: str) -> int:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func:
            return node.lineno
    raise SystemExit(f"BANK AUTHORING ERROR: no top-level def {func}() found")


def _drift_signature(source: str, func: str) -> str:
    """Widen ``func``'s signature with a keyword-only flag the body ignores.

    Used only to BUILD the counterexample workspace that proves
    ``proxy_instrument_ok`` can go false: a check calling the widened signature is
    green as-left and errors -- rather than fails -- once the inverse edit puts the
    original signature back.  That is the vacuous red the instrument must refuse to
    score as a caught regression.
    """
    lines = source.splitlines(keepends=True)
    index = _def_line(source, func) - 1
    line = lines[index]
    close = line.rindex(")")
    lines[index] = line[:close] + ", *, strict: bool = False" + line[close:]
    return "".join(lines)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _toml_str(text: str) -> str:
    return '"""\n' + text.rstrip("\n") + '\n"""'


def _task_toml(task_id: str, instruction: str, timeout: int, max_turns: int) -> str:
    return (
        f'id = "{task_id}"\n'
        f"instruction = {_toml_str(instruction)}\n\n"
        "[limits]\n"
        f"trial_timeout_s = {timeout}\n"
        f"max_turns = {max_turns}\n\n"
        "[gate]\n"
        f'run = "{GATE_CMD}"\n\n'
        "[verify]\n"
        'entry = "verify.py"\n'
        "timeout_s = 180\n"
    )


# ---------------------------------------------------------------------------
# per-class emitters
# ---------------------------------------------------------------------------
def emit_code_task(task: dict, cls: str) -> dict:
    """BUG and DATA share a layout; DATA adds the unnamed subtle cases."""
    task_id = task["id"]
    pkg = task["package"]
    mod = task["module"]
    func = task["func"]
    dotted = f"{pkg}.{mod}"
    root = bank_dir(cls) / task_id

    buggy = task["buggy"]
    fixed = task["fixed"]
    subtle = task.get("subtle_cases", [])

    # --- the authored properties, proven before anything is written -----------
    _require(
        _cases_pass(buggy, func, task["base_cases"], task_id),
        f"{task_id}: a base case FAILS on the buggy source -- the shipped suite would "
        f"start red and could manufacture a swap-back red on its own",
    )
    _require(
        not _cases_pass(buggy, func, task["edge_cases"], task_id),
        f"{task_id}: every edge case already PASSES on the buggy source -- spec_met "
        f"cannot start false and the task cannot discriminate",
    )
    _require(
        _cases_pass(fixed, func, task["edge_cases"], task_id),
        f"{task_id}: an edge case fails on the FIXED source -- the criterion is "
        f"unsatisfiable and every arm would score a manufactured null",
    )
    _require(
        _cases_pass(fixed, func, task["base_cases"], task_id),
        f"{task_id}: the fix breaks a base case -- the shipped suite would go red",
    )
    if cls == "DATA":
        _require(
            not _cases_pass(buggy, func, subtle, task_id),
            f"{task_id}: the subtle cases already pass on the buggy source -- the "
            f"co-primary has no headroom",
        )
        _require(
            _cases_pass(fixed, func, subtle, task_id),
            f"{task_id}: the subtle cases fail on the FIXED source -- unsatisfiable",
        )

    # --- fixtures -------------------------------------------------------------
    if root.exists():
        shutil.rmtree(root)
    _write(root / "fixtures" / pkg / "__init__.py", f'"""{pkg}."""\n')
    _write(root / "fixtures" / pkg / f"{mod}.py", buggy)
    _write(root / "fixtures" / "tests" / "__init__.py", "")
    _write(
        root / "fixtures" / "tests" / f"test_{mod}.py",
        _render_tests(
            BASE_TEST_HEADER, dotted, [func], [("shipped_cases", task["base_cases"], func)]
        ),
    )
    _write(root / "fixtures" / "README.md", f"# {pkg}\n\n{task['contract']}\n")

    # --- the stash the inverse edit reverts to (never inside fixtures/) --------
    _write(root / "original" / f"{mod}.py", buggy)

    # --- the reference solution (validate property 2) -------------------------
    _write(root / "solution" / pkg / f"{mod}.py", fixed)
    solution_blocks = [("reported_defect", task["edge_cases"], func)]
    if cls == "DATA":
        solution_blocks.append(("related_cases", subtle, func))
    _write(
        root / "solution" / "tests" / f"test_{mod}_regression.py",
        _render_tests(SOLUTION_TEST_HEADER, dotted, [func], solution_blocks),
    )

    # --- counterexample overlays (violability proofs, see arming.py) ----------
    _write(root / "refs" / "fix-no-check" / pkg / f"{mod}.py", fixed)
    _write(root / "refs" / "fix-vacuous-check" / pkg / f"{mod}.py", fixed)
    _write(
        root / "refs" / "fix-vacuous-check" / "tests" / f"test_{mod}_extra.py",
        _render_tests(
            SOLUTION_TEST_HEADER, dotted, [func], [("more_shipped", task["base_cases"], func)]
        ),
    )
    drifted = _drift_signature(fixed, func)
    _require(
        _cases_pass(drifted, func, task["edge_cases"], task_id),
        f"{task_id}: the drifted signature changes behaviour -- it must not",
    )
    _write(root / "refs" / "signature-drift" / pkg / f"{mod}.py", drifted)
    drift_cases = [[list(args) + [], expected] for args, expected in task["edge_cases"]]
    drift_body = []
    for args, expected in drift_cases:
        call = f"{func}({', '.join(repr(a) for a in args)}, strict=True)"
        if isinstance(expected, dict) and "raises" in expected:
            drift_body.append(f"        with self.assertRaises({expected['raises']}):")
            drift_body.append(f"            {call}")
        else:
            drift_body.append(f"        self.assertEqual({call}, {expected!r})")
    _write(
        root / "refs" / "signature-drift" / "tests" / f"test_{mod}_strict.py",
        SOLUTION_TEST_HEADER.format(dotted=dotted, func=func)
        + "    def test_strict_mode(self):\n"
        + "\n".join(drift_body)
        + '\n\n\nif __name__ == "__main__":\n    unittest.main()\n',
    )

    spec = {
        "class": cls,
        "package": pkg,
        "dotted": dotted,
        "module_filename": f"{mod}.py",
        "func": func,
        "edge_cases": task["edge_cases"],
        "criteria": ["spec_met", "regression_check_present", "proxy_instrument_ok"],
    }
    if cls == "DATA":
        spec["subtle_cases"] = subtle
        spec["criteria"].insert(1, "output_correct_on_subtle_case")
    _write(root / "spec.json", json.dumps(spec, indent=2, sort_keys=True) + "\n")
    _write(root / "verify.py", VERIFY_SHIM.format(task_id=task_id))
    _write(root / "task.toml", _task_toml(task_id, task["instruction"], 900, 45))
    return spec


def emit_trunc_task(task: dict, cls: str = "TRUNC") -> dict:
    task_id = task["id"]
    pkg = task["package"]
    mod = task["module"]
    func_a = task["func"]
    func_b = task["func_past_slice"]
    dotted = f"{pkg}.{mod}"
    root = bank_dir(cls) / task_id

    buggy = task["head"] + "\n" + task["buggy_a"] + task["middle"] + "\n" + task["buggy_b"]
    fixed = task["head"] + "\n" + task["fixed_a"] + task["middle"] + "\n" + task["fixed_b"]
    in_slice_only = task["head"] + "\n" + task["fixed_a"] + task["middle"] + "\n" + task["buggy_b"]

    _require(
        _cases_pass(buggy, func_a, task["base_cases"], task_id),
        f"{task_id}: a base case fails on the buggy source",
    )
    _require(
        not _cases_pass(buggy, func_a, task["edge_cases"], task_id),
        f"{task_id}: the in-slice defect does not show on the buggy source",
    )
    _require(
        _cases_pass(fixed, func_a, task["edge_cases"], task_id),
        f"{task_id}: the in-slice fix does not satisfy its cases",
    )
    _require(
        not _cases_pass(buggy, func_b, task["past_slice_cases"], task_id),
        f"{task_id}: the past-slice twin does not show on the buggy source -- there is "
        f"nothing past the slice to miss",
    )
    _require(
        _cases_pass(fixed, func_b, task["past_slice_cases"], task_id),
        f"{task_id}: the past-slice fix does not satisfy its cases",
    )
    _require(
        _cases_pass(in_slice_only, func_a, task["edge_cases"], task_id)
        and not _cases_pass(in_slice_only, func_b, task["past_slice_cases"], task_id),
        f"{task_id}: fixing only the in-slice occurrence does not leave the twin broken "
        f"-- the two criteria are not separable and the class measures nothing",
    )
    _require(
        _cases_pass(buggy, func_b, task["past_slice_base"], task_id),
        f"{task_id}: a past-slice base case fails on the buggy source",
    )

    # The cited range is derived from the file that ships, never hand-written.
    twin_line = _def_line(buggy, func_b)
    slice_end = twin_line - 6
    _require(
        slice_end > _def_line(buggy, func_a) + 3,
        f"{task_id}: the cited slice would not contain the in-slice defect",
    )

    if root.exists():
        shutil.rmtree(root)
    _write(root / "fixtures" / pkg / "__init__.py", f'"""{pkg}."""\n')
    _write(root / "fixtures" / pkg / f"{mod}.py", buggy)
    _write(root / "fixtures" / "tests" / "__init__.py", "")
    _write(
        root / "fixtures" / "tests" / f"test_{mod}.py",
        _render_tests(
            BASE_TEST_HEADER,
            dotted,
            [func_a, func_b],
            [
                ("shipped_cases", task["base_cases"], func_a),
                ("shipped_cases_twin", task["past_slice_base"], func_b),
            ],
        ),
    )
    _write(root / "fixtures" / "README.md", f"# {pkg}\n\n{task['contract']}\n")

    _write(root / "solution" / pkg / f"{mod}.py", fixed)
    _write(root / "refs" / "in-slice-only" / pkg / f"{mod}.py", in_slice_only)

    instruction = (
        f"A defect in `{pkg}/{mod}.py` shows up as {task['symptom']}; the reported\n"
        f"symptom points at `{pkg}/{mod}.py:1-{slice_end}`. The package README states the\n"
        f"rule this module is meant to follow. Bring the module into line with it."
    )

    spec = {
        "class": "TRUNC",
        "package": pkg,
        "dotted": dotted,
        "module_filename": f"{mod}.py",
        "func": func_a,
        "func_past_slice": func_b,
        "edge_cases": task["edge_cases"],
        "past_slice_cases": task["past_slice_cases"],
        "cited_slice_end": slice_end,
        "twin_def_line": twin_line,
        "criteria": ["spec_met", "defect_past_slice_handled"],
    }
    _write(root / "spec.json", json.dumps(spec, indent=2, sort_keys=True) + "\n")
    _write(root / "verify.py", VERIFY_SHIM.format(task_id=task_id))
    _write(root / "task.toml", _task_toml(task_id, instruction, 900, 45))
    return spec


def emit_null_task(task: dict, cls: str = "NULL") -> dict:
    task_id = task["id"]
    pkg = task["package"]
    mod = task["module"]
    root = bank_dir(cls) / task_id

    _require(
        task["must_not_contain"] in task["source"] or "README" in task["edit_file"],
        f"{task_id}: the stale text is not present in the shipped module",
    )

    if root.exists():
        shutil.rmtree(root)
    _write(root / "fixtures" / pkg / "__init__.py", f'"""{pkg}."""\n')
    _write(root / "fixtures" / pkg / f"{mod}.py", task["source"])
    _write(root / "fixtures" / "tests" / "__init__.py", "")
    _write(root / "fixtures" / "tests" / f"test_{mod}.py", task["tests"])
    for name, body in (task.get("extra_files") or {}).items():
        _write(root / "fixtures" / name, body)

    # The reference solution: the edit and nothing else.
    edited_target = task["edit_file"]
    if edited_target.endswith(".md"):
        original = (task.get("extra_files") or {})[edited_target]
        edited = original.replace(task["must_not_contain"], task["must_contain"])
    else:
        edited = task["source"].replace(task["must_not_contain"], task["must_contain"])
    _require(
        edited != (task["source"] if not edited_target.endswith(".md") else original),
        f"{task_id}: the reference edit is a no-op",
    )
    _write(root / "solution" / edited_target, edited)

    # The over-scope counterexample: the same edit PLUS a check nobody asked for.
    _write(root / "refs" / "edit-plus-checks" / edited_target, edited)
    _write(
        root / "refs" / "edit-plus-checks" / "tests" / f"test_{mod}_extra.py",
        "import unittest\n\n\n"
        "class ExtraChecks(unittest.TestCase):\n"
        "    def test_module_imports(self):\n"
        f"        import {pkg}.{mod}  # noqa: F401\n\n\n"
        'if __name__ == "__main__":\n    unittest.main()\n',
    )

    baseline = {
        f"tests/test_{mod}.py": _sha256(task["tests"]),
    }
    spec = {
        "class": "NULL",
        "package": pkg,
        "edit_file": edited_target,
        "must_contain": task["must_contain"],
        "must_not_contain": task["must_not_contain"],
        "baseline_checks": baseline,
        "criteria": ["spec_met", "scope_respected"],
    }
    _write(root / "spec.json", json.dumps(spec, indent=2, sort_keys=True) + "\n")
    _write(root / "verify.py", VERIFY_SHIM.format(task_id=task_id))
    _write(root / "task.toml", _task_toml(task_id, task["instruction"], 600, 25))
    return spec


def _sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# gate check: the shipped suite must be green on the untouched fixture
# ---------------------------------------------------------------------------
def _gate_green(cls: str, task_id: str) -> bool:
    root = bank_dir(cls) / task_id / "fixtures"
    env = dict(os.environ)
    # A fixture tree must ship no bytecode cache: a stale .pyc whose (mtime, size)
    # still matches shadows an edited source, and the inverse edit then reads the
    # pre-edit module.  Arming caught that on trunc-plural before any spend.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-q"],
        cwd=str(root),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    if proc.returncode != 0:
        print(f"  gate RED on {task_id}:\n{proc.stdout}\n{proc.stderr}", file=sys.stderr)
    return proc.returncode == 0


def _write_bank_toml(bank: Path, name: str, holdout: list[str]) -> None:
    rows = "\n".join(f'    "{h}",' for h in holdout)
    body = f"holdout = [\n{rows}\n]\n" if holdout else "holdout = []\n"
    _write(
        bank / "bank.toml",
        f'name = "{name}"\ndataset_version = "{DATASET_VERSION}"\n{body}',
    )


def _emit_strong_bank(cls: str, ids: list[str]) -> list[str]:
    """Copy the pre-declared subsample of *cls* into its strong-tier bank.

    ``refs/`` is deliberately left behind: those overlays exist to arm the verifier,
    and the arming run proves the instrument on the weak bank's copy of the task.
    What must hold instead is that the strong bank's task is byte-identical to that
    proven copy, which :func:`_check_strong_equivalence` asserts.
    """
    source_bank = bank_dir(cls)
    target = TASKS_DIR / STRONG_BANKS[cls]
    if target.exists():
        shutil.rmtree(target)
    chosen = [task_id for task_id in ids if task_id not in HOLDOUT][:STRONG_K]
    _require(
        len(chosen) == STRONG_K,
        f"{cls}: only {len(chosen)} non-holdout tasks for a subsample of {STRONG_K}",
    )
    for task_id in chosen:
        for item in ("fixtures", "original", "solution", "spec.json", "verify.py", "task.toml"):
            src = source_bank / task_id / item
            if not src.exists():
                continue
            dst = target / task_id / item
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
    shutil.copytree(source_bank / "_lib", target / "_lib")
    _write_bank_toml(target, STRONG_BANKS[cls], [])
    return chosen


def _check_strong_equivalence(cls: str, chosen: list[str]) -> None:
    weak = bank_dir(cls)
    strong = TASKS_DIR / STRONG_BANKS[cls]
    for task_id in chosen:
        for path in sorted((strong / task_id).rglob("*")):
            if not path.is_file():
                continue
            twin = weak / task_id / path.relative_to(strong / task_id)
            _require(
                twin.is_file() and twin.read_bytes() == path.read_bytes(),
                f"{cls}/{task_id}: {path.name} differs from the weak bank's proven copy",
            )


def main() -> int:
    ids_by_class: dict[str, list[str]] = {}
    for cls in CLASS_BANKS:
        target = bank_dir(cls)
        if target.exists():
            shutil.rmtree(target)

    for task in BUG:
        emit_code_task(task, "BUG")
        ids_by_class.setdefault("BUG", []).append(task["id"])
    for task in DATA:
        emit_code_task(task, "DATA")
        ids_by_class.setdefault("DATA", []).append(task["id"])
    for task in TRUNC:
        emit_trunc_task(task)
        ids_by_class.setdefault("TRUNC", []).append(task["id"])
    for task in NULL:
        emit_null_task(task)
        ids_by_class.setdefault("NULL", []).append(task["id"])

    all_ids = [task_id for ids in ids_by_class.values() for task_id in ids]
    _require(len(set(all_ids)) == len(all_ids), "duplicate task id")
    for holdout_id in HOLDOUT:
        _require(holdout_id in all_ids, f"holdout id {holdout_id} is not a task")

    lib = (HERE / "proxy_lib.py").read_text(encoding="utf-8")
    for cls in CLASS_BANKS:
        _write(bank_dir(cls) / "_lib" / "proxy.py", lib)

    red = [
        task_id
        for cls, ids in ids_by_class.items()
        for task_id in ids
        if not _gate_green(cls, task_id)
    ]
    _require(not red, f"the shipped suite is not green on these fixtures: {red}")

    for cls, ids in ids_by_class.items():
        _write_bank_toml(bank_dir(cls), CLASS_BANKS[cls], [h for h in HOLDOUT if h in ids])

    strong_chosen: dict[str, list[str]] = {}
    for cls in STRONG_BANKS:
        strong_chosen[cls] = _emit_strong_bank(cls, ids_by_class[cls])

    for cache in list(TASKS_DIR.rglob("__pycache__")):
        if "verif-lift" in str(cache):
            shutil.rmtree(cache, ignore_errors=True)
    leftover = [str(p) for p in TASKS_DIR.rglob("*.pyc") if "verif-lift" in str(p)]
    _require(not leftover, f"bytecode left in the bank tree: {leftover[:5]}")

    for cls, chosen in strong_chosen.items():
        _check_strong_equivalence(cls, chosen)

    print("generated banks:")
    for cls, ids in ids_by_class.items():
        sealed = [h for h in HOLDOUT if h in ids]
        print(
            f"  {CLASS_BANKS[cls]:26} {len(ids):3} tasks  "
            f"holdout {len(sealed)}  screening pool {len(ids) - len(sealed)}"
        )
    for cls, chosen in strong_chosen.items():
        print(f"  {STRONG_BANKS[cls]:26} {len(chosen):3} tasks  (pre-declared subsample)")
    print(f"  sealed holdout: {', '.join(HOLDOUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
