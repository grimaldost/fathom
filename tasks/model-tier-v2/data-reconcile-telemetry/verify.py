"""Acceptance verifier for data-reconcile-telemetry (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed original ``recon/match.py`` and the shipped suite — come from
this task directory; both are identical for every arm, so reading them leaks no
scenario identity (ADR-0003).

**Genre: data reconciliation, fully covered.** The instruction names all three edit
sites, so no cross-shape trigger fires and the rubric score is the additive total
alone: breadth, domain rules, and a brief that demands both the rules document and the
package conventions. That combination is what puts it in the strong band with no
shortcut keyword anywhere near it — the cell the bank had no rung in, and the one that
asks whether the additive points buy anything the floor and the shortcuts do not.

Its headroom is not a hidden fix site but an intricate specified contract: an inclusive
bound, a three-level tie-break, and a count that has to reconcile across two modules.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates on
``standard`` only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "recon"
MODULE = "match.py"
BUGGY_ORIGINAL = HERE / "original" / "match.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "recon_imports",
    "matches_the_worked_example",
    "tolerance_bound_is_inclusive",
    "tie_break_follows_the_rules",
    "no_regression",
    "regression_test_present",
]


def _api(view: Path):
    """(Reading, Device, match, gaps, summarise) from the candidate package."""
    model = bv.import_candidate(view, f"{PACKAGE}.model", PACKAGE)
    match_mod = bv.import_candidate(view, f"{PACKAGE}.match", PACKAGE)
    gaps_mod = bv.import_candidate(view, f"{PACKAGE}.gaps", PACKAGE)
    report_mod = bv.import_candidate(view, f"{PACKAGE}.report", PACKAGE)
    if any(m is None for m in (model, match_mod, gaps_mod, report_mod)):
        raise RuntimeError("a recon module did not import")
    return (
        model.Reading,
        model.Device,
        match_mod.match,
        gaps_mod.gaps,
        report_mod.summarise,
    )


def _worked_example(view: Path) -> bool:
    """RULES.md's worked example: M3's reading order, and nothing else.

    Deliberately independent of the inclusive bound (20 is strictly inside 25) and of
    the tie-break (one device), so a patch that fixes the reported example banks
    neither of the standard-level criteria for free.
    """
    reading, device, match, _gaps, _summarise = _api(view)
    readings = [reading(2, 140, 6.0), reading(1, 100, 5.0)]
    devices = [device("d1", 120, 25)]
    return match(readings, devices) == [(1, "d1")]


def _inclusive_bound(view: Path) -> bool:
    """M1's bound is `<=`. Exactly at the tolerance must match, one past must not."""
    reading, device, match, _gaps, _summarise = _api(view)
    at_bound = match([reading(1, 100, 5.0)], [device("d1", 110, 10)])
    past_bound = match([reading(1, 100, 5.0)], [device("d1", 111, 10)])
    return at_bound == [(1, "d1")] and past_bound == []


def _tie_break(view: Path) -> bool:
    """M2: nearest, then earlier `seen_at`, then lower id — none of it input order."""
    reading, device, match, _gaps, _summarise = _api(view)
    nearest = match([reading(1, 100, 5.0)], [device("d1", 108, 10), device("d2", 102, 10)])
    earlier = match([reading(1, 100, 5.0)], [device("d9", 105, 10), device("d1", 95, 10)])
    lower_id = match([reading(1, 100, 5.0)], [device("d9", 105, 10), device("d1", 105, 10)])
    return nearest == [(1, "d2")] and earlier == [(1, "d1")] and lower_id == [(1, "d1")]


def _counts_reconcile(view: Path) -> bool:
    """S1 plus the convention that counts are over READINGS, not devices.

    The last case is the one that separates: two unmatched readings sharing an `at`.
    G1 says that is two gaps, so `matched + gaps` still equals `readings`. A `gaps`
    that reads "listed once" as "one per timestamp" collapses them, every standard
    criterion still passes, and the counts stop reconciling.
    """
    reading, device, match, gaps, summarise = _api(view)
    cases = [
        ([reading(1, 100, 5.0), reading(2, 9000, 1.0)], [device("d1", 100, 5)]),
        (
            [reading(1, 100, 5.0), reading(2, 103, 5.0)],
            [device("d1", 101, 5), device("d2", 104, 5)],
        ),
        ([reading(1, 100, 5.0)], []),
        ([reading(1, 100, 5.0), reading(2, 100, 6.0)], []),
    ]
    for readings, devices in cases:
        pairs = match(readings, devices)
        gap_ids = gaps(readings, pairs)
        got = summarise(readings, pairs, gap_ids)
        if got.get("readings") != len(readings):
            return False
        if got.get("matched") != len(pairs) or got.get("gaps") != len(gap_ids):
            return False
        if got["matched"] + got["gaps"] != got["readings"]:
            return False
    return True


def _gaps_are_the_unmatched(view: Path) -> bool:
    """G1: every unmatched reading, once, ascending by `at` then id — deterministic."""
    reading, device, match, gaps, _summarise = _api(view)
    readings = [reading(3, 900, 1.0), reading(1, 100, 5.0), reading(2, 100, 6.0)]
    pairs = match(readings, [device("d1", 100, 2)])
    matched = {rid for rid, _did in pairs}
    expected = [
        r.id for r in sorted(readings, key=lambda r: (r.at, str(r.id))) if r.id not in matched
    ]
    return gaps(readings, pairs) == expected


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])

    results = {
        # --- thin: the package loads and the reported example comes out right -----
        "recon_imports": bv.check(lambda: len(_api(view)) == 5),
        "matches_the_worked_example": bv.check(lambda: _worked_example(view)),
        # --- standard: the two matching rules the worked example does not pin -----
        "tolerance_bound_is_inclusive": bv.check(lambda: _inclusive_bound(view)),
        "tie_break_follows_the_rules": bv.check(lambda: _tie_break(view)),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: the counts have to reconcile ACROSS the three modules, under
        #     the convention that they count readings and not devices. A patch that
        #     gets both matching rules right and counts devices passes the whole
        #     standard oracle and fails here. -------------------------------------
        "counts_reconcile_over_readings": bv.check(lambda: _counts_reconcile(view)),
        "gaps_are_exactly_the_unmatched": bv.check(lambda: _gaps_are_the_unmatched(view)),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
