"""Acceptance verifier for fix-nonlocal-urlkey (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/normalize.py``) and the shipped
suite (``original/tests/``) — come from this task directory; both are identical for
every arm, so reading them leaks no scenario identity (ADR-0003). Emits a flat
``{criterion: bool}`` JSON object and exits 0 iff every criterion holds.

NON-LOCAL root-cause task. The symptom (pages split by query string / trailing slash)
shows up in ``page_counts`` and ``top_page``, but the real bug is the shared
``page_key`` returning the URL raw. A band-aid that canonicalizes inside ``page_counts``
fixes ``page_counts_merge`` yet leaves ``top_page`` (a second, independent caller of
``page_key``) broken; only fixing ``page_key`` (the root cause) passes both.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "urlstats"
MODULE = "normalize.py"
BUGGY_ORIGINAL = HERE / "original" / "normalize.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _report(view):
    return bv.import_candidate(view, "urlstats.report", PACKAGE)


def _page_counts_merge(view: Path) -> bool:
    """page_counts merges URLs that differ only by query string / trailing slash."""
    mod = _report(view)
    if mod is None or not hasattr(mod, "page_counts"):
        return False
    try:
        got = dict(mod.page_counts(["/home", "/home/", "/home?ref=promo"]))
        return got == {"/home": 3}
    except Exception:
        return False


def _top_page_merge(view: Path) -> bool:
    """top_page picks the right winner once query/slash variants are merged.

    Defeats a band-aid that only canonicalizes inside page_counts: top_page calls
    page_key itself, so without the root fix it still sees three distinct pages and
    returns the first-seen ('/b') instead of the true winner ('/a').
    """
    mod = _report(view)
    if mod is None or not hasattr(mod, "top_page"):
        return False
    try:
        return mod.top_page(["/b", "/a", "/a/", "/a?x=1"]) == "/a"
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "page_counts_merge": _page_counts_merge(view),
        "top_page_merge": _top_page_merge(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
