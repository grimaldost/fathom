"""Shared, scenario-blind helpers for the model-tier-v2 verifiers.

Harness-side library: it sits beside the task dirs (never inside any ``fixtures/``)
so ``taskbank.stage_task`` never copies it into a workspace and the grading
result-view never contains it. It carries NO scenario / arm identity — every arm's
``verify.py`` calls the same code with the same task-fixed references (the stashed
buggy source and the shipped test suite), so using it cannot bias the blind A/B
comparison (ADR-0003). Each ``verify.py`` reads the candidate's work solely from
``argv[1]`` (the result-view) and its task-constant references solely from its own
task directory.

Two groups of helpers.

**Layout-agnostic primitives** (carried over from ``model-tier-v1/bugfix_verify.py``,
unchanged in behaviour so the two banks grade the same way):

* ``import_candidate`` — import the candidate package whether it is flat
  (``pkg/mod.py``) or under ``src/`` (``src/pkg/mod.py``).
* ``no_regression`` — run the *shipped* suite (a harness-side copy, so a candidate
  cannot weaken ``no_regression`` by editing the tests in the workspace) against the
  candidate source.
* ``regression_test_present`` — the swap: run the candidate's own suite on their
  source (must be green), swap the stashed buggy original back in, run again (must
  go red). Red here can only come from a candidate-added, bug-covering test because
  the shipped suite passes on the buggy source by construction.

**Oracle-split helpers** (new in v2). Every task in this bank emits ONE criterion
dict covering all three nested oracle levels — ``thin`` ⊂ ``standard`` ⊂ ``strong``
(``oracles.toml``) — and the exit code gates on the ``standard`` level, which is the
``model-tier-v1`` contract. See ``README.md`` § *Oracle quality is a criterion slice,
not an arm* for why the crossing needs no extra arms.

* ``check`` — evaluate one criterion, mapping any exception to ``False`` (a verifier
  that crashes on a broken candidate would score the trial an error, not a fail).
* ``emit`` — print the flat ``{criterion: bool}`` JSON and return the exit code.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

# --------------------------------------------------------------- layout helpers


def find_package_dir(view: Path, package: str) -> Path | None:
    """Return the directory of *package* under *view* (flat or src-layout)."""
    for base in (view / package, view / "src" / package):
        if (base / "__init__.py").is_file():
            return base
    for cand in view.rglob(f"{package}/__init__.py"):
        return cand.parent
    return None


def import_root_for(view: Path, package: str) -> Path | None:
    """Return the directory to place on ``sys.path`` so ``import <package>`` works."""
    pkg = find_package_dir(view, package)
    return pkg.parent if pkg is not None else None


def find_module_file(view: Path, package: str, filename: str) -> Path | None:
    """Locate ``<package>/<filename>`` under *view*, layout-agnostic."""
    pkg = find_package_dir(view, package)
    if pkg is not None:
        cand = pkg / filename
        if cand.is_file():
            return cand
    for cand in view.rglob(f"{package}/{filename}"):
        return cand
    return None


def find_tests_dir(view: Path) -> Path | None:
    """Locate the test directory under *view*, preferring the conventional layout."""
    for base in (view / "tests", view / "src" / "tests"):
        if base.is_dir():
            return base
    for cand in view.rglob("tests"):
        if cand.is_dir() and any(cand.glob("test_*.py")):
            return cand
    return None


def import_candidate(view: Path, dotted: str, package: str):  # noqa: ANN201 - a module or None
    """Import *dotted* (e.g. ``"ndj.merge"``) from the candidate *view*.

    Returns the module, or ``None`` on any failure. Safe to call repeatedly within a
    single process for different views of the same package: the package's cached
    submodules are purged first and the inserted root is removed afterwards, so a
    later call re-imports cleanly from a different location.
    """
    root = import_root_for(view, package)
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


def _suite_env(view: Path) -> dict[str, str]:
    """Env for the test subprocess: candidate package importable, UTF-8 stdout."""
    env = dict(os.environ)
    roots = [str(view)]
    if (view / "src").is_dir():
        roots.append(str(view / "src"))
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(roots + ([existing] if existing else []))
    env["PYTHONUTF8"] = "1"
    return env


def run_test_suite(view: Path, tests_dir: Path | None = None) -> bool:
    """Run the unittest suite under *view*; return ``True`` iff it exits 0.

    Layout-agnostic: discovers from ``view/tests`` (or ``src/tests``) with both
    ``view`` and ``view/src`` on ``PYTHONPATH`` so the candidate package imports
    whether flat or under ``src/``. A missing test directory is ``False`` — no
    suite is not a green suite.
    """
    if tests_dir is None:
        tests_dir = find_tests_dir(view)
    if tests_dir is None:
        return False
    cmd = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(tests_dir),
        "-t",
        str(view),
        "-p",
        "test_*.py",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=_suite_env(view),
            cwd=str(view),
            timeout=45,
        )
    except Exception:
        return False
    return proc.returncode == 0


def no_regression(view: Path, shipped_tests_dir: Path) -> bool:
    """True iff the *shipped* suite passes against the candidate source.

    The canonical shipped tests (*shipped_tests_dir*, harness-side) are overlaid
    onto a throwaway copy of *view*, replacing whatever tests the candidate left in
    the workspace, so this measures only whether existing behavior still holds — not
    whether the candidate's own added tests pass. Never mutates ``argv[1]``.
    """
    if not Path(shipped_tests_dir).is_dir():
        return False
    tmp = tempfile.mkdtemp(prefix="fathom-noregress-")
    try:
        work = Path(tmp) / "view"
        shutil.copytree(view, work)
        for existing in (work / "tests", work / "src" / "tests"):
            if existing.is_dir():
                shutil.rmtree(existing, ignore_errors=True)
        shutil.copytree(shipped_tests_dir, work / "tests")
        return run_test_suite(work, tests_dir=work / "tests")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def regression_test_present(
    view: Path, package: str, module_filename: str, buggy_source: Path
) -> bool:
    """True iff the candidate added a test that actually covers the planted bug.

    Operates on a throwaway copy of *view* (never mutates ``argv[1]``):

    1. Run the candidate's own suite on their source — it must be green.
    2. Swap the stashed buggy original (*buggy_source*) back in at the discovered
       module location and run the same suite — it must go red.

    The shipped suite passes on the buggy source by construction, so a red in
    step 2 can only come from a candidate-added, bug-covering test. A heavy refactor
    that moves the bug logic out of *module_filename* is the known false-negative;
    the focused "fix this bug" tasks make that case rare.
    """
    buggy_source = Path(buggy_source)
    if not buggy_source.is_file():
        return False
    tmp = tempfile.mkdtemp(prefix="fathom-regress-")
    try:
        work = Path(tmp) / "view"
        shutil.copytree(view, work)
        if not run_test_suite(work):
            return False
        target = find_module_file(work, package, module_filename)
        if target is None:
            return False
        target.write_text(buggy_source.read_text(encoding="utf-8"), encoding="utf-8")
        return not run_test_suite(work)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------- oracle-split helpers


def check(fn: Callable[[], bool]) -> bool:
    """Evaluate one criterion, mapping any exception (and any non-bool) to ``False``.

    A criterion that raises on a broken candidate must read as a FAILED criterion,
    not as a crashed verifier: an ``error`` outcome is dropped from the calibration
    entirely, which would silently delete exactly the trials the bank exists to
    measure.
    """
    try:
        return bool(fn())
    except Exception:
        return False


def emit(criteria: dict[str, bool], standard: Sequence[str]) -> int:
    """Print the flat criterion dict and return the exit code.

    The exit code gates on the ``standard`` oracle level only — the
    ``model-tier-v1`` contract — even though the dict also carries the ``thin``
    subset and the ``strong`` superset. Grading the exit code on ``strong`` would
    silently redefine "correct" for this bank against every sibling bank.
    """
    print(json.dumps(criteria, sort_keys=True))
    missing = [c for c in standard if c not in criteria]
    if missing:  # an authoring error, not a candidate failure — fail loudly
        print(
            f"verify: standard criteria missing from the emitted dict: {missing}", file=sys.stderr
        )
        return 1
    return 0 if all(criteria[c] for c in standard) else 1
