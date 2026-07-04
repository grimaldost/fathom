"""Acceptance verifier for fix-clamp (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/core.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003). Emits a flat
``{criterion: bool}`` JSON object and exits 0 iff every criterion holds.

This is the trivial low rung: even a weak model should fix it. The planted bug only
clamps the lower bound, so ``clamp_in_range`` (anchor) and ``clamp_low`` already pass
on the buggy source; ``clamp_high`` is the one that fails until the upper bound is
restored. The shipped suite covers only the in-range and below-range cases, so it
passes on the buggy source by construction.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "numkit"
MODULE = "core.py"
BUGGY_ORIGINAL = HERE / "original" / "core.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _clamp(view):
    mod = bv.import_candidate(view, "numkit.core", PACKAGE)
    return getattr(mod, "clamp", None) if mod is not None else None


def _clamp_in_range(view: Path) -> bool:
    """A value already inside the range is returned unchanged (anchor; the shipped
    suite covers this)."""
    fn = _clamp(view)
    if fn is None:
        return False
    try:
        return fn(5, 0, 10) == 5
    except Exception:
        return False


def _clamp_low(view: Path) -> bool:
    """A value below the low bound is raised to ``lo``."""
    fn = _clamp(view)
    if fn is None:
        return False
    try:
        return fn(-3, 0, 10) == 0
    except Exception:
        return False


def _clamp_high(view: Path) -> bool:
    """A value above the high bound is capped at ``hi`` (the planted bug)."""
    fn = _clamp(view)
    if fn is None:
        return False
    try:
        return fn(99, 0, 10) == 10
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "clamp_in_range": _clamp_in_range(view),
        "clamp_low": _clamp_low(view),
        "clamp_high": _clamp_high(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
