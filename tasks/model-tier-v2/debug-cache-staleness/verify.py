"""Acceptance verifier for debug-cache-staleness (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed original ``feedcache/keys.py`` and the shipped suite — come
from this task directory; both are identical for every arm, so reading them leaks no
scenario identity (ADR-0003).

**Genre: unlocalised debugging.** Every other rung's instruction points at the file or
the call whose behaviour is wrong. This one names no file at all: the arm is given a
symptom and a contract and has to localise the fault itself. That is the routing shape
the bank was missing, and it is a different demand from "fix the named thing" even at
the same rubric score.

The planted cause is in ``feedcache/keys.py``: the cache keys carry the tenant but not
the day, so a value computed before midnight is served after it. Three views share
those builders; the report names one.

Every check drives the views through their public signatures, so a candidate is free
to scope the key, change the store, or restructure the module — only the answers are
graded.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates on
``standard`` only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "feedcache"
MODULE = "keys.py"
BUGGY_ORIGINAL = HERE / "original" / "keys.py"
SHIPPED_TESTS = HERE / "original" / "tests"

DAY1 = "2026-03-01"
DAY2 = "2026-03-02"

STANDARD = [
    "feedcache_imports",
    "summary_is_cached_within_one_day",
    "summary_fresh_across_midnight",
    "report_fresh_across_midnight",
    "no_regression",
    "regression_test_present",
]


def _views(view: Path):
    """(store_factory, summary, daily_report, trend) from the candidate package."""
    store_mod = bv.import_candidate(view, f"{PACKAGE}.store", PACKAGE)
    api = bv.import_candidate(view, f"{PACKAGE}.api", PACKAGE)
    report = bv.import_candidate(view, f"{PACKAGE}.report", PACKAGE)
    trend = bv.import_candidate(view, f"{PACKAGE}.trend", PACKAGE)
    mods = (store_mod, api, report, trend)
    if any(m is None for m in mods):
        raise RuntimeError("a feedcache module did not import")
    return (
        store_mod.Store,
        api.summary,
        report.daily_report,
        trend.trend,
    )


def _fresh_across_days(view: Path, which: int, first, second, read) -> bool:
    """Cache *first* on DAY1, ask the same view about DAY2, and read the answer.

    ``which`` selects the view (1 summary, 2 report, 3 trend). The answer for DAY2
    must be computed from DAY2's data, not served from DAY1's entry.
    """
    factory, *fns = _views(view)
    fn = fns[which - 1]
    store = factory()
    fn(store, "acme", DAY1, first)
    got = fn(store, "acme", DAY2, second)
    return read(got)


def _scoped_on_both_axes(view: Path) -> bool:
    """Every view answers (tenant, day) as a pair — the independent sweep.

    Neither axis is named in the instruction, and the tenant axis already works, so
    this is not a restatement of the reported symptom: it is the property the whole
    package is supposed to hold, checked on all three views at once.
    """
    factory, *fns = _views(view)
    payloads = ([1, 2, 3], [7], [5, 1], [1, 5])
    for fn in fns:
        store = factory()
        base = fn(store, "acme", DAY1, payloads[0])
        for tenant, day in (("acme", DAY2), ("beta", DAY1), ("beta", DAY2)):
            other = fn(store, tenant, day, payloads[1])
            if other == base:
                return False
            if other.get("tenant") != tenant or other.get("day") != day:
                return False
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])

    def cached_within_a_day() -> bool:
        factory, summary, _report, _trend = _views(view)
        store = factory()
        first = summary(store, "acme", DAY1, [1, 2, 3])
        return summary(store, "acme", DAY1, [1, 2, 3]) == first

    results = {
        # --- thin: the package still loads, and caching still works inside a day --
        "feedcache_imports": bv.check(lambda: len(_views(view)) == 4),
        "summary_is_cached_within_one_day": bv.check(cached_within_a_day),
        # --- standard: the reported view is fresh across midnight, and so is the
        #     second consumer of the same key builders, which nothing named --------
        "summary_fresh_across_midnight": bv.check(
            lambda: _fresh_across_days(view, 1, [1, 2, 3], [7], lambda g: g["total"] == 7)
        ),
        "report_fresh_across_midnight": bv.check(
            lambda: _fresh_across_days(view, 2, [1, 2, 3], [7], lambda g: g["rows"] == 1)
        ),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: the third consumer, and an independent sweep over BOTH scoping
        #     axes on all three views. A patch that reaches two of the three key
        #     builders satisfies the whole standard oracle and fails here. ----------
        "trend_fresh_across_midnight": bv.check(
            lambda: _fresh_across_days(view, 3, [5, 1], [1, 5], lambda g: g["direction"] == "up")
        ),
        "every_view_is_day_and_tenant_scoped": bv.check(lambda: _scoped_on_both_axes(view)),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
