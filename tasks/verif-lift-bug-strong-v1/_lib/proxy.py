"""Shared, scenario-blind verifier logic for the verif-lift-v1 bank.

Extends the ``e1-verif`` swap-the-work-back proxy (``tasks/e1-verif/*/verify.py``)
in the two places that decided whether that instrument could be trusted:

1. **The revert is an inverse edit, not a checkout.**  ``e1-verif`` wrote the whole
   stashed original over the candidate's module file, which discards whatever else
   the candidate put in that file -- helpers, imports, comments -- and so
   manufactures reds that have nothing to do with a regression guard.  Here the
   revert replaces **exactly one function's source segment** (located with ``ast``
   on the candidate's own file) with the stashed original's segment for the same
   function, and asserts byte equality of every byte outside that segment.  That is
   the discipline the measured skill states as a bright line, and a bank that
   measures the discipline has to obey it.

2. **A red is only counted when it is an assertion failure.**  Reverting new code
   commonly makes a check *error* (import failure, ``TypeError`` from a signature
   the candidate widened).  Scoring an error as a caught regression manufactures
   lift out of nothing.  The check harness reports failures and errors separately;
   an error-only red scores the proxy False and flips ``proxy_instrument_ok`` so the
   vacuous-red rate is recoverable per cell rather than silently inflating a lift.

Every criterion this module emits is "good when true", so a per-criterion pass rate
reads the same direction everywhere.  ``scope_respected`` is the false-positive
guard: the plan's ``over_scope`` is ``1 - scope_respected``.

Blindness (ADR-0003): the only inputs are ``argv[1]`` (the result view) and
task-constant files that live in the task directory and are identical for every arm.
Fails CLOSED on any error.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# The check harness, run as a subprocess against whatever checks a candidate left.
# Handles unittest.TestCase subclasses and bare ``test_*`` functions (pytest style,
# run without pytest).  Prints ``RAN=<n> FAIL=<f> ERR=<e>``.
# Exit: 0 all-passed (n>0) | 1 something was not green | 2 import error | 3 no tests.
# ---------------------------------------------------------------------------
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
            print("RAN=0 FAIL=0 ERR=1")
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
        print("RAN=0 FAIL=0 ERR=0")
        return 3
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=0).run(suite)
    n_fail = len(result.failures)
    n_err = len(result.errors)
    print("RAN=%d FAIL=%d ERR=%d" % (count, n_fail, n_err))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
"""

_CHECK_TIMEOUT_S = 45


# ---------------------------------------------------------------------------
# Workspace layout
# ---------------------------------------------------------------------------
def find_package_dir(view: Path, package: str) -> Path | None:
    for base in (view / package, view / "src" / package):
        if (base / "__init__.py").is_file():
            return base
    for cand in view.rglob(f"{package}/__init__.py"):
        return cand.parent
    return None


def find_module_file(view: Path, package: str, module_filename: str) -> Path | None:
    pkg = find_package_dir(view, package)
    if pkg is not None and (pkg / module_filename).is_file():
        return pkg / module_filename
    for cand in view.rglob(f"{package}/{module_filename}"):
        return cand
    return None


def import_root(view: Path, package: str) -> Path | None:
    pkg = find_package_dir(view, package)
    return pkg.parent if pkg is not None else None


def _suite_env(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    roots = [str(root)]
    if (root / "src").is_dir():
        roots.append(str(root / "src"))
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(roots + ([existing] if existing else []))
    env["PYTHONUTF8"] = "1"
    # No new bytecode, and (with purge_bytecode) none inherited either.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def purge_bytecode(root: Path) -> None:
    """Remove every ``__pycache__`` under *root*.

    Not hygiene -- correctness.  CPython validates a cached ``.pyc`` against the
    source's (mtime, size) pair, and the inverse edit changes a file's content while
    a sibling copy of it may carry a cache compiled from the pre-edit source.  When
    the pair happens to match, the interpreter runs the STALE bytecode and the
    swap-back comes up green on code that was in fact reverted -- a systematic false
    negative on the primary criterion, arriving silently and only on some tasks.
    Arming caught exactly that on one task before any spend.  ``root`` is always a
    throwaway copy, so removing the cache changes nothing a candidate wrote.
    """
    for cache in list(root.rglob("__pycache__")):
        shutil.rmtree(cache, ignore_errors=True)


# ---------------------------------------------------------------------------
# Correctness: import the candidate and evaluate declared cases
# ---------------------------------------------------------------------------
def _normalize(value: Any) -> Any:
    """Tuples compare equal to lists; everything else is left alone."""
    if isinstance(value, tuple):
        return [_normalize(v) for v in value]
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    return value


def import_candidate(view: Path, package: str, dotted: str):
    root = import_root(view, package)
    if root is None:
        return None
    for key in [k for k in sys.modules if k == package or k.startswith(package + ".")]:
        del sys.modules[key]
    root_str = str(root)
    sys.path.insert(0, root_str)
    try:
        return importlib.import_module(dotted)
    except Exception:
        return None
    finally:
        try:
            sys.path.remove(root_str)
        except ValueError:
            pass


def cases_hold(view: Path, package: str, dotted: str, func: str, cases: list[Any]) -> bool:
    """True iff every declared case holds against the candidate's own module.

    A case is ``[args, expected]``.  ``expected`` may be ``{"raises": "<ExcName>"}``
    to declare that the call must raise.  Computed by importing the candidate
    directly, independent of whatever checks the candidate did or did not leave.
    """
    mod = import_candidate(view, package, dotted)
    if mod is None or not hasattr(mod, func):
        return False
    fn = getattr(mod, func)
    for case in cases:
        args, expected = case[0], case[1]
        wants_raise = isinstance(expected, dict) and "raises" in expected
        try:
            got = fn(*args)
        except Exception as exc:  # noqa: BLE001 - a raise may be the declared outcome
            if wants_raise and type(exc).__name__ == expected["raises"]:
                continue
            return False
        if wants_raise:
            return False
        if _normalize(got) != _normalize(expected):
            return False
    return True


# ---------------------------------------------------------------------------
# The check runner
# ---------------------------------------------------------------------------
def discover_check_files(root: Path) -> list[Path]:
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


def _run_harness(root: Path, files: list[Path]) -> tuple[int, int, int, int]:
    """(returncode, ran, failures, errors) for the candidate's unittest-style checks."""
    fd, hpath = tempfile.mkstemp(prefix="vlift-harness-", suffix=".py")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(_HARNESS_SRC)
        cmd = [sys.executable, hpath, *[str(f) for f in files]]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=_suite_env(root),
                cwd=str(root),
                timeout=_CHECK_TIMEOUT_S,
            )
        except Exception:  # noqa: BLE001 - a broken harness is an errored check run
            return 1, 0, 0, 1
        ran = fails = errs = 0
        for line in proc.stdout.splitlines():
            if line.startswith("RAN="):
                for part in line.split():
                    key, _, val = part.partition("=")
                    try:
                        num = int(val)
                    except ValueError:
                        continue
                    if key == "RAN":
                        ran = num
                    elif key == "FAIL":
                        fails = num
                    elif key == "ERR":
                        errs = num
        return proc.returncode, ran, fails, errs
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
            encoding="utf-8",
            errors="replace",
            env=_suite_env(root),
            cwd=str(root),
            timeout=_CHECK_TIMEOUT_S,
        )
        return proc.returncode
    except Exception:  # noqa: BLE001
        return 1


def run_checks(root: Path) -> dict[str, Any]:
    """Run every check the candidate left; classify the outcome.

    Returns ``{"status": "green"|"red"|"empty", "ran": n, "failures": f, "errors": e}``.
    ``failures`` counts assertion failures; ``errors`` counts import errors,
    ``TypeError``s from a widened signature, and anything else that is not an
    assertion.  The distinction is the whole point: only a failure is evidence that
    a check pins behaviour.
    """
    all_files = discover_check_files(root)
    test_mods = [p for p in all_files if p.name not in ("check.py", "checks.py")]
    scripts = [p for p in all_files if p.name in ("check.py", "checks.py")]

    ran = fails = errs = 0
    not_green = False
    if test_mods:
        rc, n, f, e = _run_harness(root, test_mods)
        ran += n
        fails += f
        errs += e
        if rc == 3:
            pass  # this batch contributed no tests
        elif rc != 0:
            not_green = True
    for script in scripts:
        ran += 1
        if _run_script(root, script) != 0:
            not_green = True
            # A bare script gives no failure/error split; count it as a failure so a
            # candidate who writes check.py instead of tests is not penalised.
            fails += 1
    if not_green:
        return {"status": "red", "ran": ran, "failures": fails, "errors": errs}
    if ran == 0:
        return {"status": "empty", "ran": 0, "failures": 0, "errors": 0}
    return {"status": "green", "ran": ran, "failures": 0, "errors": 0}


# ---------------------------------------------------------------------------
# The inverse edit
# ---------------------------------------------------------------------------
def _function_segment(source: str, func: str) -> tuple[int, int] | None:
    """(start, end) character offsets of ``func``'s top-level definition in *source*.

    Includes any decorators, so a candidate-added decorator travels with the body it
    decorates.  ``None`` when the function is absent or the file does not parse.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    lines = source.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != func:
            continue
        first = node.decorator_list[0].lineno if node.decorator_list else node.lineno
        end = node.end_lineno
        if end is None:
            return None
        return starts[first - 1], starts[end]
    return None


def inverse_edit(candidate_source: str, original_source: str, func: str) -> str | None:
    """*candidate_source* with only ``func``'s definition replaced by the original's.

    Returns ``None`` when the edit is not expressible -- the candidate deleted or
    renamed the function, or either file no longer parses.  Every byte outside the
    replaced segment is preserved exactly; that is what makes this a revert of the
    functional diff rather than a checkout of the file.
    """
    cand_span = _function_segment(candidate_source, func)
    orig_span = _function_segment(original_source, func)
    if cand_span is None or orig_span is None:
        return None
    c_start, c_end = cand_span
    o_start, o_end = orig_span
    reverted = (
        candidate_source[:c_start] + original_source[o_start:o_end] + candidate_source[c_end:]
    )
    # Byte-precision assertion: nothing outside the segment moved.
    if reverted[:c_start] != candidate_source[:c_start]:
        return None
    if reverted[len(reverted) - (len(candidate_source) - c_end) :] != candidate_source[c_end:]:
        return None
    return reverted


def swap_back_probe(
    view: Path,
    package: str,
    module_filename: str,
    func: str,
    original_path: Path,
    *,
    fix_landed: bool = False,
) -> dict[str, Any]:
    """Run the candidate's checks as-left, then again with ``func`` reverted.

    ``verdict`` is one of:

    ``guarded``      as-left green, reverted red **by assertion** -- a real guard.
    ``unguarded``    as-left green, reverted still green -- no guard, or a vacuous one.
    ``not_green``    the candidate's own checks are not green as-left, or it left none.
    ``vacuous_red``  reverted red only through errors -- the revert broke the check
                     rather than tripping it; the instrument saw nothing.
    ``infeasible``   the inverse edit is not expressible, or it is a no-op on a
                     workspace where the defect IS fixed -- the fix lives outside
                     ``func`` (in a module constant, a new helper, a different file),
                     so reverting ``func`` reverts nothing and the probe can read
                     nothing.  Scoring that as "no guard" would be a silent false
                     negative; it is reported as an instrument miss instead, and the
                     per-cell rate of these is what Gate 0 reads.
    """
    if not original_path.is_file():
        return {"verdict": "infeasible", "why": "stashed original missing"}

    as_left = run_checks(view)
    if as_left["status"] != "green":
        return {"verdict": "not_green", "as_left": as_left}

    target = find_module_file(view, package, module_filename)
    if target is None:
        return {"verdict": "infeasible", "why": "module file not found in the result view"}

    try:
        candidate_source = target.read_text(encoding="utf-8")
        original_source = original_path.read_text(encoding="utf-8")
    except OSError:
        return {"verdict": "infeasible", "why": "source unreadable"}

    reverted = inverse_edit(candidate_source, original_source, func)
    if reverted is None:
        return {"verdict": "infeasible", "why": f"no inverse edit for {func}()"}
    if fix_landed and reverted == candidate_source:
        return {
            "verdict": "infeasible",
            "why": f"the defect is fixed but {func}() is byte-identical to the original "
            f"-- the fix lives outside the reverted unit, so the probe reads nothing",
        }

    tmp = tempfile.mkdtemp(prefix="vlift-swap-")
    try:
        work = Path(tmp) / "view"
        shutil.copytree(view, work)
        purge_bytecode(work)
        work_target = find_module_file(work, package, module_filename)
        if work_target is None:
            return {"verdict": "infeasible", "why": "module file lost in the copy"}
        work_target.write_text(reverted, encoding="utf-8")
        after = run_checks(work)
        if after["status"] != "red":
            return {"verdict": "unguarded", "after": after}
        if after["failures"] > 0:
            return {"verdict": "guarded", "after": after}
        return {"verdict": "vacuous_red", "after": after}
    except Exception as exc:  # noqa: BLE001 - fail closed
        return {"verdict": "infeasible", "why": f"{type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Scope (the false-positive guard for the NULL class)
# ---------------------------------------------------------------------------
def scope_respected(view: Path, baseline_checks: dict[str, str]) -> bool:
    """True when the candidate left the check surface exactly as it found it.

    *baseline_checks* maps a repo-relative path to the sha256 of the shipped file.
    Over-scope is any added check file, any removed one, or any edit to one -- the
    behaviour that got the prescriptive arm rejected for firing on 58% of trivial
    edits.
    """
    import hashlib

    found: dict[str, str] = {}
    for p in discover_check_files(view):
        rel = p.relative_to(view).as_posix()
        try:
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            return False
        found[rel] = digest
    return found == baseline_checks


# ---------------------------------------------------------------------------
# Class drivers -- one per task class.  Each returns the flat criteria dict.
# ---------------------------------------------------------------------------
def _footprint_criteria(probe: dict[str, Any]) -> dict[str, bool]:
    verdict = probe["verdict"]
    return {
        "regression_check_present": verdict == "guarded",
        "proxy_instrument_ok": verdict not in ("vacuous_red", "infeasible"),
    }


def grade(spec: dict[str, Any], task_dir: Path, view: Path) -> dict[str, bool]:
    """The criteria for one trial, dispatched on the task's declared class."""
    purge_bytecode(view)
    cls = spec["class"]
    pkg = spec.get("package", "")
    dotted = spec.get("dotted", "")

    if cls in ("BUG", "DATA"):
        criteria = {
            "spec_met": cases_hold(view, pkg, dotted, spec["func"], spec["edge_cases"]),
        }
        if cls == "DATA":
            criteria["output_correct_on_subtle_case"] = cases_hold(
                view, pkg, dotted, spec["func"], spec["subtle_cases"]
            )
        probe = swap_back_probe(
            view,
            pkg,
            spec["module_filename"],
            spec["func"],
            task_dir / "original" / spec["module_filename"],
            fix_landed=criteria["spec_met"],
        )
        criteria.update(_footprint_criteria(probe))
        return criteria

    if cls == "TRUNC":
        return {
            "spec_met": cases_hold(view, pkg, dotted, spec["func"], spec["edge_cases"]),
            "defect_past_slice_handled": cases_hold(
                view, pkg, dotted, spec["func_past_slice"], spec["past_slice_cases"]
            ),
        }

    if cls == "NULL":
        return {
            "spec_met": _null_edit_done(view, spec),
            "scope_respected": scope_respected(view, spec["baseline_checks"]),
        }

    raise ValueError(f"unknown task class {cls!r}")


def _null_edit_done(view: Path, spec: dict[str, Any]) -> bool:
    """The trivial edit landed: the required text is present and the stale text gone."""
    target = view / spec["edit_file"]
    if not target.is_file():
        return False
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return False
    if spec["must_contain"] not in text:
        return False
    return spec["must_not_contain"] not in text


def main(task_dir: Path, argv: list[str]) -> int:
    """Entry point every task's ``verify.py`` shim calls.

    Exits 0 iff ``spec_met`` (the correctness gate); every other criterion rides as
    a reported criterion, which is where the discriminating signal lives.
    """
    if len(argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(argv[1])
    try:
        spec = json.loads((task_dir / "spec.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - fail closed
        print(json.dumps({"spec_unreadable": False, "detail": str(exc)[:200]}))
        return 1
    try:
        criteria = grade(spec, task_dir, view)
    except Exception:  # noqa: BLE001 - fail closed
        keys = spec.get("criteria", ["spec_met"])
        criteria = dict.fromkeys(keys, False)
    print(json.dumps(criteria, sort_keys=True))
    return 0 if criteria.get("spec_met") else 1
