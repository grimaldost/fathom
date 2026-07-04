"""Acceptance verifier for fix-titlecase (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/core.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003). Emits a flat
``{criterion: bool}`` JSON object and exits 0 iff every criterion holds.

This is the trivial low rung (near the weak/mid boundary): even a weak model should
fix it. The planted bug indexes ``word[0]`` without guarding the empty word (so the
empty string raises) and never lower-cases the remainder of a word. ``title_basic``
(anchor) already passes on the buggy source; ``title_empty`` and ``title_mixed_case``
fail until both defects are fixed. The shipped suite covers only a simple all-lower
input, so it passes on the buggy source by construction.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "textkit"
MODULE = "core.py"
BUGGY_ORIGINAL = HERE / "original" / "core.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _title_case(view):
    mod = bv.import_candidate(view, "textkit.core", PACKAGE)
    return getattr(mod, "title_case", None) if mod is not None else None


def _title_basic(view: Path) -> bool:
    """A plain lower-case sentence title-cases (anchor; the shipped suite covers this)."""
    fn = _title_case(view)
    if fn is None:
        return False
    try:
        return fn("hello world") == "Hello World"
    except Exception:
        return False


def _title_empty(view: Path) -> bool:
    """The empty string maps to the empty string (must not raise)."""
    fn = _title_case(view)
    if fn is None:
        return False
    try:
        return fn("") == ""
    except Exception:
        return False


def _title_mixed_case(view: Path) -> bool:
    """The remainder of each word is lower-cased, not left verbatim (the planted bug)."""
    fn = _title_case(view)
    if fn is None:
        return False
    try:
        return fn("hELLO wORLD") == "Hello World"
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "title_basic": _title_basic(view),
        "title_empty": _title_empty(view),
        "title_mixed_case": _title_mixed_case(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
