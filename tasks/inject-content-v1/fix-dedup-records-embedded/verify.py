"""Acceptance verifier for fix-dedup-records (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/core.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003). Emits a flat
``{criterion: bool}`` JSON object and exits 0 iff every criterion holds.

The discriminator is correctness, not just test-discipline: the bug report names only
the *case* symptom, but the documented contract also requires surrounding-whitespace
normalization and keep-first semantics. A symptom-only fix (add ``.lower()``) passes
``dedup_case`` but fails ``dedup_whitespace`` / ``keeps_first_row``; only a fix that
honors the whole documented contract passes all three.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "records"
MODULE = "core.py"
BUGGY_ORIGINAL = HERE / "original" / "core.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _dedupe(view):
    mod = bv.import_candidate(view, "records.core", PACKAGE)
    return getattr(mod, "dedupe", None) if mod is not None else None


def _dedup_case(view: Path) -> bool:
    """Case-variant names collapse to one (the symptom names this case)."""
    fn = _dedupe(view)
    if fn is None:
        return False
    try:
        out = fn([{"name": "Ada"}, {"name": "ADA"}, {"name": "ada"}])
        return len(out) == 1
    except Exception:
        return False


def _dedup_whitespace(view: Path) -> bool:
    """Surrounding whitespace is ignored — documented, but NOT hinted by the symptom."""
    fn = _dedupe(view)
    if fn is None:
        return False
    try:
        out = fn(
            [{"name": "Ada Lovelace"}, {"name": "  Ada Lovelace "}, {"name": "Ada Lovelace  "}]
        )
        return len(out) == 1
    except Exception:
        return False


def _keeps_first_row(view: Path) -> bool:
    """The FIRST row of each person is kept unmodified, in first-appearance order.

    A fix that collapses via ``{normalize(name): row}`` keeps the *last* duplicate
    and fails this; a first-wins fix passes.
    """
    fn = _dedupe(view)
    if fn is None:
        return False
    try:
        rows = [
            {"name": "Ada", "id": 1},
            {"name": "Grace", "id": 2},
            {"name": "ada", "id": 3},
            {"name": " grace ", "id": 4},
        ]
        out = fn(rows)
        return out == [{"name": "Ada", "id": 1}, {"name": "Grace", "id": 2}]
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "dedup_case": _dedup_case(view),
        "dedup_whitespace": _dedup_whitespace(view),
        "keeps_first_row": _keeps_first_row(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
