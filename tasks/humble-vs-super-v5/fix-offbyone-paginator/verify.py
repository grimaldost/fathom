"""Acceptance verifier for fix-offbyone-paginator (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/core.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003). Emits a flat
``{criterion: bool}`` JSON object and exits 0 iff every criterion holds.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "paginator"
MODULE = "core.py"
BUGGY_ORIGINAL = HERE / "original" / "core.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _fix_correct(view: Path) -> bool:
    """Hidden test: the page count must round a partial final page up.

    The shipped suite only uses exact multiples, so the planted floor-division bug
    (and a naive ``// + 1`` over-fix) both pass it; these cases catch both.
    """
    mod = bv.import_candidate(view, "paginator.core", PACKAGE)
    if mod is None:
        return False
    try:
        tp = mod.total_pages
        return (
            tp(25, 10) == 3
            and tp(99, 10) == 10
            and tp(1, 10) == 1
            and tp(1, 1) == 1
            and tp(0, 10) == 0
            and tp(20, 10) == 2
            and tp(50, 25) == 2
        )
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "fix_correct": _fix_correct(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
