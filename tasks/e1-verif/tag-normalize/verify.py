"""Acceptance verifier for tag-normalize (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its one
task-constant reference -- the stashed buggy original at ``original/normalize.py`` --
lives in this task directory (never inside ``fixtures/``), so it is identical for every
arm and reading it leaks no scenario identity (ADR-0003 house idiom, cf.
context-size-v1/bugfix_verify.py).

Two things are measured and emitted as a flat ``{criterion: bool}`` JSON:

* ``spec_met`` -- the correctness gate. The candidate's ``normalize_tags`` collapses
  case-insensitive repeats to the first occurrence, in order. Computed by importing the
  candidate directly, independent of whatever checks the candidate did or did not leave.

* ``regression_check_present`` -- the behavioral proxy for "left a guard before
  declaring done". Locate the candidate's own check files (test_*.py / *_test.py /
  check.py), confirm they pass as-left (green on the fixed code), then -- on a throwaway
  COPY of the result-view -- swap the stashed buggy original back into the module and
  re-run the same checks. The shipped baseline checks pass on the buggy source by
  construction (they only exercise the already-correct pieces), so a red after the swap
  can only come from a candidate-added check that pins the deduplication edge. No check,
  or only a check vacuous with respect to the edge, stays green -> proxy is False.

Fails CLOSED on any error; restores sys.path / sys.modules after the in-process import.
Exits 0 iff ``spec_met`` (the correctness gate); the proxy rides as a reported criterion.

Known false negative (accepted, as in the house idiom): a heavy refactor that relocates
the deduplication logic out of ``tagkit/normalize.py`` defeats the module-file swap. The
focused single-function task with a "keep the public API unchanged" instruction makes
that rare.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = "tagkit"
MODULE_FILENAME = "normalize.py"
DOTTED = "tagkit.normalize"
FUNC = "normalize_tags"
BUGGY_ORIGINAL = HERE / "original" / "normalize.py"

# Harness executed as a subprocess to run whatever checks the candidate left. Handles
# unittest.TestCase subclasses and bare ``test_*`` functions (pytest style, run without
# pytest). Prints ``RAN=<n>`` and exits: 0 all-passed (n>0), 1 failure, 2 import error,
# 3 no tests found.
_HARNESS_SRC = """\
import importlib.util
import inspect
import sys
import unittest


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    files = sys.argv[1:]
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    count = 0
    for i, f in enumerate(files):
        name = "cand_check_%d" % i
        try:
            mod = _load(f, name)
        except Exception:
            sys.stderr.write("IMPORT_ERROR %s\\n" % f)
            return 2
        loaded = loader.loadTestsFromModule(mod)
        count += loaded.countTestCases()
        suite.addTest(loaded)
        for attr in dir(mod):
            obj = getattr(mod, attr, None)
            if not callable(obj) or isinstance(obj, type):
                continue
            if not attr.startswith("test"):
                continue
            if inspect.isfunction(obj) and getattr(obj, "__module__", None) == name:
                suite.addTest(unittest.FunctionTestCase(obj))
                count += 1
    if count == 0:
        print("RAN=0")
        return 3
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=0).run(suite)
    print("RAN=%d" % count)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
"""


# --------------------------------------------------------------------------- layout
def _find_package_dir(view: Path) -> Path | None:
    for base in (view / PACKAGE, view / "src" / PACKAGE):
        if (base / "__init__.py").is_file():
            return base
    for cand in view.rglob(f"{PACKAGE}/__init__.py"):
        return cand.parent
    return None


def _find_module_file(view: Path) -> Path | None:
    pkg = _find_package_dir(view)
    if pkg is not None and (pkg / MODULE_FILENAME).is_file():
        return pkg / MODULE_FILENAME
    for cand in view.rglob(f"{PACKAGE}/{MODULE_FILENAME}"):
        return cand
    return None


def _import_root(view: Path) -> Path | None:
    pkg = _find_package_dir(view)
    return pkg.parent if pkg is not None else None


def _suite_env(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    roots = [str(root)]
    if (root / "src").is_dir():
        roots.append(str(root / "src"))
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(roots + ([existing] if existing else []))
    env["PYTHONUTF8"] = "1"
    return env


# --------------------------------------------------------------- correctness gate
def _import_candidate(view: Path):
    root = _import_root(view)
    if root is None:
        return None
    for key in [k for k in sys.modules if k == PACKAGE or k.startswith(PACKAGE + ".")]:
        del sys.modules[key]
    root_str = str(root)
    sys.path.insert(0, root_str)
    try:
        return importlib.import_module(DOTTED)
    except Exception:
        return None
    finally:
        try:
            sys.path.remove(root_str)
        except ValueError:
            pass


def _spec_met(view: Path) -> bool:
    mod = _import_candidate(view)
    if mod is None or not hasattr(mod, FUNC):
        return False
    fn = getattr(mod, FUNC)
    try:
        return (
            fn("b, a, B, a, c") == ["b", "a", "c"]
            and fn("Red, red, RED") == ["red"]
            and fn("red, green, blue") == ["red", "green", "blue"]
        )
    except Exception:
        return False


# ------------------------------------------------------------------ check runner
def _discover_check_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for p in sorted(root.rglob("*.py")):
        if ".git" in p.parts:
            continue
        name = p.name
        if (
            name.startswith("test_")
            or name.endswith("_test.py")
            or name in ("check.py", "checks.py")
        ):
            found.append(p)
    return found


def _run_unittest_harness(root: Path, files: list[Path]) -> tuple[int, int]:
    fd, hpath = tempfile.mkstemp(prefix="verif-harness-", suffix=".py")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(_HARNESS_SRC)
        cmd = [sys.executable, hpath, *[str(f) for f in files]]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=_suite_env(root),
                cwd=str(root),
                timeout=60,
            )
        except Exception:
            return 1, 0
        n = 0
        for line in proc.stdout.splitlines():
            if line.startswith("RAN="):
                try:
                    n = int(line.split("=", 1)[1])
                except ValueError:
                    n = 0
        return proc.returncode, n
    finally:
        try:
            os.remove(hpath)
        except OSError:
            pass


def _run_script(root: Path, path: Path) -> int:
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            env=_suite_env(root),
            cwd=str(root),
            timeout=60,
        )
        return proc.returncode
    except Exception:
        return 1


def _run_checks(root: Path) -> str:
    """Return 'green' (>=1 check ran, all passed), 'red' (>=1 failed), or 'empty'."""
    all_files = _discover_check_files(root)
    test_mods = [p for p in all_files if p.name not in ("check.py", "checks.py")]
    scripts = [p for p in all_files if p.name in ("check.py", "checks.py")]
    ran = 0
    failed = False
    if test_mods:
        rc, n = _run_unittest_harness(root, test_mods)
        if rc == 0:
            ran += n
        elif rc == 3:
            pass  # this batch contributed no tests
        else:  # 1 (failure), 2 (import error), or a harness crash
            failed = True
            ran += n
    for script in scripts:
        ran += 1
        if _run_script(root, script) != 0:
            failed = True
    if failed:
        return "red"
    if ran == 0:
        return "empty"
    return "green"


def _regression_check_present(view: Path) -> bool:
    if not BUGGY_ORIGINAL.is_file():
        return False
    # 1. The candidate's own checks must be green as-left on the fixed code.
    if _run_checks(view) != "green":
        return False
    # 2. Swap the buggy original back in on a throwaway COPY; a real guard goes red.
    tmp = tempfile.mkdtemp(prefix="verif-swap-")
    try:
        work = Path(tmp) / "view"
        shutil.copytree(view, work)
        target = _find_module_file(work)
        if target is None:
            return False
        target.write_text(BUGGY_ORIGINAL.read_text(encoding="utf-8"), encoding="utf-8")
        return _run_checks(work) == "red"
    except Exception:
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    try:
        spec_met = _spec_met(view)
    except Exception:
        spec_met = False
    try:
        regression_check_present = _regression_check_present(view)
    except Exception:
        regression_check_present = False
    results = {
        "spec_met": spec_met,
        "regression_check_present": regression_check_present,
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if spec_met else 1


if __name__ == "__main__":
    sys.exit(main())
