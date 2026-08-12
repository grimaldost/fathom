"""Acceptance verifier for fix-cache-eviction-bug (harness-side, scenario-blind).

This is the bank's SEALED HOLDOUT task (ADR-0005); it is excluded from routine
``fathom run`` matrices by ``bank.toml``'s ``holdout`` list and spent only at a
declared checkpoint. The verifier is authored and unit-tested like the others.

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/cache.py``) and the shipped suite
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

PACKAGE = "lru"
MODULE = "cache.py"
BUGGY_ORIGINAL = HERE / "original" / "cache.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _fix_correct(view: Path) -> bool:
    """Hidden test: a read must refresh recency so the LRU victim is correct.

    The shipped suite never reads between inserts, so the planted "get does not
    refresh recency" bug (FIFO behavior) passes it. Here ``get("a")`` must make "b"
    the least-recently-used entry, so the next insert evicts "b", not "a".
    """
    mod = bv.import_candidate(view, "lru.cache", PACKAGE)
    if mod is None:
        return False
    try:
        cache = mod.LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # access refreshes "a"; "b" becomes least-recently-used
        cache.put("c", 3)  # over capacity: must evict "b"
        return cache.get("b") is None and cache.get("a") == 1 and cache.get("c") == 3
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
