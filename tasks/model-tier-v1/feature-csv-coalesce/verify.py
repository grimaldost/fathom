"""Acceptance verifier for feature-csv-coalesce (harness-side, scenario-blind, ADR-0003).

Reads ONLY argv[1] (the result-view path); carries no scenario/arm identity; runs
offline. Imports the candidate ``csvcoalesce`` package and grades:

  behavior_correct - the hidden happy-path suite passes. This is the correctness
                     gate: the process exit code is 0 iff this holds. The edge
                     criteria ride alongside as the discriminating per-criterion
                     signal (a rushed solution clears the gate yet trips an edge).
  empty_input      - empty / blank-only input returns [].
  ragged_rows      - short rows pad missing trailing columns with None; extra
                     cells are ignored.
  type_coercion    - cells coerce to their column type; a present-but-empty cell
                     becomes None without raising.
  tests_present    - the candidate's OWN tests genuinely exercise the edges: they
                     pass against the candidate's code AND fail against a
                     happy-path-correct naive mutant (a mutation kill). A
                     happy-path-only suite does not count.

Every criterion is defensive: any exception yields False, so a missing or broken
feature scores a *fail*, never an *error*. Emits a flat {criterion: bool} JSON
object; exits 0 iff behavior_correct.
"""

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

PKG = "csvcoalesce"
SUBMODULES = ("parse", "coalesce")

# A happy-path-correct naive mutant: it reads clean full rows fine, but truncates
# ragged rows (zip stops at the shortest) and leaves empty cells un-coalesced /
# crashes on empty typed cells. Used only to check whether the candidate's tests
# actually exercise the edges (a happy-only suite cannot tell it from a correct
# one). Mirrors the public surface so the candidate's imports resolve.
_MUT_MODEL = """\
from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    name: str
    type: str
"""

_MUT_PARSE = """\
import csv
import io


def parse_csv(text, columns):
    records = []
    for row in csv.reader(io.StringIO(text)):
        record = {}
        for col, cell in zip(columns, row):
            if col.type == "int":
                record[col.name] = int(cell)
            elif col.type == "float":
                record[col.name] = float(cell)
            else:
                record[col.name] = cell
        records.append(record)
    return records
"""

_MUT_INIT = (
    "from .model import Column\nfrom .parse import parse_csv\n\n__all__ = ['Column', 'parse_csv']\n"
)

# Stdlib test runner: collects both unittest.TestCase classes and bare test_*
# functions (pytest-style), so the candidate's tests are run whatever style they
# chose. Prints {"collected": n, "failed": m} as JSON.
_RUNNER_SRC = """\
import importlib.util
import json
import sys
import types
import unittest


class _FuncCase(unittest.TestCase):
    def __init__(self, fn):
        super().__init__("runTest")
        self._fn = fn

    def runTest(self):
        self._fn()


def _load(path, idx):
    name = "candmod_%d" % idx
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    test_files = json.loads(sys.argv[1])
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    import_failures = 0
    for idx, path in enumerate(test_files):
        try:
            mod = _load(path, idx)
        except Exception:
            import_failures += 1
            continue
        for attr in dir(mod):
            obj = getattr(mod, attr, None)
            if (
                isinstance(obj, type)
                and issubclass(obj, unittest.TestCase)
                and obj is not unittest.TestCase
            ):
                for case in loader.loadTestsFromTestCase(obj):
                    suite.addTest(case)
        for attr in dir(mod):
            if attr.startswith("test"):
                obj = getattr(mod, attr, None)
                if isinstance(obj, types.FunctionType):
                    suite.addTest(_FuncCase(obj))
    result = unittest.TestResult()
    suite.run(result)
    collected = result.testsRun + import_failures
    failed = len(result.failures) + len(result.errors) + import_failures
    print(json.dumps({"collected": collected, "failed": failed}))


if __name__ == "__main__":
    main()
"""


def _find_pkg_init(view: Path) -> Path | None:
    for cand in (view / PKG / "__init__.py", view / "src" / PKG / "__init__.py"):
        if cand.is_file():
            return cand
    for cand in view.rglob("__init__.py"):
        if "__pycache__" in cand.parts:
            continue
        if cand.parent.name == PKG:
            return cand
    return None


def _pkg_root(view: Path) -> str | None:
    init = _find_pkg_init(view)
    return str(init.parent.parent) if init else None


def _load_pkg(view: Path):
    root = _pkg_root(view)
    if root is None:
        return None
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        return importlib.import_module(PKG)
    except Exception:
        return None


def _get(mod, attr):
    if mod is None:
        return None
    if hasattr(mod, attr):
        return getattr(mod, attr)
    for sub in SUBMODULES:
        try:
            m = importlib.import_module(f"{PKG}.{sub}")
        except Exception:
            continue
        if hasattr(m, attr):
            return getattr(m, attr)
    return None


def _cols(Column):
    return [Column("id", "int"), Column("name", "str"), Column("score", "float")]


def _behavior_correct(parse_csv, Column) -> bool:
    cols = _cols(Column)
    rows = parse_csv("1,Alice,9.5\n2,Bob,8.0", cols)
    if rows != [
        {"id": 1, "name": "Alice", "score": 9.5},
        {"id": 2, "name": "Bob", "score": 8.0},
    ]:
        return False
    if not (isinstance(rows[0]["id"], int) and isinstance(rows[0]["score"], float)):
        return False
    return parse_csv("5,Zed,4.0", cols) == [{"id": 5, "name": "Zed", "score": 4.0}]


def _empty_input(parse_csv, Column) -> bool:
    cols = _cols(Column)
    return parse_csv("", cols) == [] and parse_csv("\n\n", cols) == []


def _ragged_rows(parse_csv, Column) -> bool:
    cols = _cols(Column)
    short = parse_csv("3", cols) == [{"id": 3, "name": None, "score": None}]
    partial = parse_csv("6,Carol", cols) == [{"id": 6, "name": "Carol", "score": None}]
    extra = parse_csv("9,Eve,1.0,EXTRA", cols) == [{"id": 9, "name": "Eve", "score": 1.0}]
    return short and partial and extra


def _type_coercion(parse_csv, Column) -> bool:
    cols = _cols(Column)
    typed = parse_csv("8,Dora,3", cols)
    ok_types = (
        typed == [{"id": 8, "name": "Dora", "score": 3.0}]
        and isinstance(typed[0]["id"], int)
        and isinstance(typed[0]["score"], float)
    )
    empties = parse_csv("7,,", cols) == [{"id": 7, "name": None, "score": None}]
    return ok_types and empties


def _discover_tests(view: Path) -> list[Path]:
    found: dict[str, Path] = {}
    for pat in ("test_*.py", "*_test.py"):
        for p in view.rglob(pat):
            if "__pycache__" in p.parts:
                continue
            found[str(p)] = p
    return [found[k] for k in sorted(found)]


def _run_suite(view: Path, test_files: list[Path], roots: list[str]) -> dict | None:
    with tempfile.TemporaryDirectory() as rdir:
        runner = Path(rdir) / "runner.py"
        runner.write_text(_RUNNER_SRC, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(roots)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            proc = subprocess.run(
                [sys.executable, "-B", str(runner), json.dumps([str(p) for p in test_files])],
                cwd=str(view),
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception:
            return None
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except Exception:
                return None
    return None


def _write_mutant(dest: Path) -> None:
    pkg = dest / PKG
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(_MUT_INIT, encoding="utf-8")
    (pkg / "model.py").write_text(_MUT_MODEL, encoding="utf-8")
    (pkg / "parse.py").write_text(_MUT_PARSE, encoding="utf-8")


def _tests_present(view: Path) -> bool:
    test_files = _discover_tests(view)
    if not test_files:
        return False
    root = _pkg_root(view) or str(view)
    cand = _run_suite(view, test_files, [root, str(view)])
    if not cand or cand.get("collected", 0) < 1 or cand.get("failed", 1) != 0:
        return False
    with tempfile.TemporaryDirectory() as mdir:
        _write_mutant(Path(mdir))
        mut = _run_suite(view, test_files, [mdir, str(view)])
    if not mut:
        return False
    return mut.get("failed", 0) >= 1


def _safe(fn, parse_csv, Column) -> bool:
    if parse_csv is None or Column is None:
        return False
    try:
        return bool(fn(parse_csv, Column))
    except Exception:
        return False


def _safe_call(fn, *args) -> bool:
    try:
        return bool(fn(*args))
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    mod = _load_pkg(view)
    parse_csv = _get(mod, "parse_csv")
    Column = _get(mod, "Column")
    results = {
        "behavior_correct": _safe(_behavior_correct, parse_csv, Column),
        "empty_input": _safe(_empty_input, parse_csv, Column),
        "ragged_rows": _safe(_ragged_rows, parse_csv, Column),
        "type_coercion": _safe(_type_coercion, parse_csv, Column),
        "tests_present": _safe_call(_tests_present, view),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if results["behavior_correct"] else 1


if __name__ == "__main__":
    sys.exit(main())
