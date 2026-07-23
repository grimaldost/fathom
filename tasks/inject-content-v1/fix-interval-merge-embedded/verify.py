"""Acceptance verifier for fix-interval-merge (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/core.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003). Emits a flat
``{criterion: bool}`` JSON object and exits 0 iff every criterion holds.

Two independent, documented edge cases discriminate: a rushed fix typically handles
one and forgets the other. ``merge_adjacent`` needs the touching boundary
(``start <= last_end + 1``); ``merge_contained`` needs the merged end to be the
*greatest* end (``max``), not the latest. The shipped suite exercises neither, so a
naive fix can pass it and still fail one criterion.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "intervals"
MODULE = "core.py"
BUGGY_ORIGINAL = HERE / "original" / "core.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _merge(view):
    mod = bv.import_candidate(view, "intervals.core", PACKAGE)
    return getattr(mod, "merge", None) if mod is not None else None


def _as_pairs(result):
    """Coerce a merge result to a list of tuples (container type is enforced by the
    shipped suite via no_regression, so the logic criteria stay container-agnostic)."""
    return [tuple(x) for x in result]


def _merge_overlap(view: Path) -> bool:
    """Plain overlap merges (the shipped suite covers this — an anchor)."""
    fn = _merge(view)
    if fn is None:
        return False
    try:
        return _as_pairs(fn([(1, 4), (3, 6)])) == [(1, 6)]
    except Exception:
        return False


def _merge_adjacent(view: Path) -> bool:
    """Touching intervals (consecutive integers) merge — documented boundary case."""
    fn = _merge(view)
    if fn is None:
        return False
    try:
        return _as_pairs(fn([(1, 3), (4, 6)])) == [(1, 6)] and _as_pairs(
            fn([(1, 2), (3, 4), (5, 6)])
        ) == [(1, 6)]
    except Exception:
        return False


def _merge_contained(view: Path) -> bool:
    """A short interval inside a longer one must NOT shorten the merged end."""
    fn = _merge(view)
    if fn is None:
        return False
    try:
        return _as_pairs(fn([(1, 10), (2, 5)])) == [(1, 10)] and _as_pairs(
            fn([(1, 8), (2, 4), (3, 9)])
        ) == [(1, 9)]
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "merge_overlap": _merge_overlap(view),
        "merge_adjacent": _merge_adjacent(view),
        "merge_contained": _merge_contained(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
