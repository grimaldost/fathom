"""Acceptance verifier for fix-tz-dst-normalize (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/dst.py``) and the shipped suite
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

PACKAGE = "eastern"
MODULE = "dst.py"
BUGGY_ORIGINAL = HERE / "original" / "dst.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _fix_correct(view: Path) -> bool:
    """Hidden test: the UTC offset must follow the exact DST transition days.

    The shipped suite uses only mid-winter / mid-summer dates. These cases pin both
    sides of the spring transition (2026-03-08 02:00) and the autumn transition
    (2026-11-01 02:00), so the planted month-only bug AND a naive ``3 <= month <= 11``
    over-fix each fail at least one.
    """
    mod = bv.import_candidate(view, "eastern.dst", PACKAGE)
    if mod is None:
        return False
    try:
        f = mod.to_utc
        return (
            f(2026, 1, 15, 12, 0) == "2026-01-15T17:00:00Z"  # winter -> EST
            and f(2026, 7, 15, 12, 0) == "2026-07-15T16:00:00Z"  # summer -> EDT
            and f(2026, 3, 20, 12, 0) == "2026-03-20T16:00:00Z"  # after 2nd Sun Mar -> EDT
            and f(2026, 3, 3, 12, 0) == "2026-03-03T17:00:00Z"  # before 2nd Sun Mar -> EST
            and f(2026, 11, 5, 12, 0) == "2026-11-05T17:00:00Z"  # after 1st Sun Nov -> EST
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
