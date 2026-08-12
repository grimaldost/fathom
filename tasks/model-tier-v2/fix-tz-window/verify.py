"""Acceptance verifier for fix-tz-window (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/window.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003).

Displaced cause. The symptom is reported in ``report.hours_in_day``; the fault is the
``start + 1440`` in ``window.day_window``, which every consumer of a day window
inherits. A patch inside ``hours_in_day`` fixes the reported number and leaves
``report.slots`` running an hour past local midnight on the two transition days —
which is where the standard oracle sits. The strong oracle checks the window
boundary itself, over every day of the year, through the ``day_window`` API the
instruction never names.

The expected offsets are restated here from the README rather than read from the
candidate's ``tz`` module, so the check does not inherit a candidate's rewrite.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates
on ``standard`` only.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "daycal"
MODULE = "window.py"
BUGGY_ORIGINAL = HERE / "original" / "window.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "hours_ordinary_day",
    "hours_spring_forward",
    "hours_fall_back",
    "slots_cover_transition_day",
    "no_regression",
    "regression_test_present",
]

AHEAD_FROM = date(2026, 3, 9)
AHEAD_THROUGH = date(2026, 11, 1)
SHORT_DAY = date(2026, 3, 8)  # 23 hours — the day the instruction names
LONG_DAY = date(2026, 11, 1)  # 25 hours — never named
ORDINARY = date(2026, 6, 15)
YEAR_DAYS = [date(2026, 1, 1) + timedelta(days=i) for i in range(365)]


def expected_midnight(day: date) -> int:
    """UTC minute stamp of local midnight, computed from the documented rules."""
    offset = -240 if AHEAD_FROM <= day <= AHEAD_THROUGH else -300
    return day.toordinal() * 1440 - offset


def _slots_cover(mod, day: date, count: int) -> bool:
    parts = mod.slots(day, count)
    if len(parts) != count:
        return False
    start, end = expected_midnight(day), expected_midnight(day + timedelta(days=1))
    contiguous = all(parts[i][1] == parts[i + 1][0] for i in range(count - 1))
    return parts[0][0] == start and parts[-1][1] == end and contiguous


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])
    report = bv.import_candidate(view, "daycal.report", PACKAGE)
    window = bv.import_candidate(view, "daycal.window", PACKAGE)

    results = {
        # --- thin: the anchor plus the day the instruction names ------------------
        "hours_ordinary_day": bv.check(lambda: report.hours_in_day(ORDINARY) == 24.0),
        "hours_spring_forward": bv.check(lambda: report.hours_in_day(SHORT_DAY) == 23.0),
        # --- standard: the other transition day, and the second consumer of the
        #     day window — neither is named in the instruction ---------------------
        "hours_fall_back": bv.check(lambda: report.hours_in_day(LONG_DAY) == 25.0),
        "slots_cover_transition_day": bv.check(
            lambda: (
                _slots_cover(report, SHORT_DAY, 4)
                and _slots_cover(report, LONG_DAY, 5)
                and _slots_cover(report, ORDINARY, 6)
            )
        ),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: the boundary itself, over every day of the year -------------
        "window_bounds_every_day": bv.check(
            lambda: all(
                window.day_window(d)
                == (expected_midnight(d), expected_midnight(d + timedelta(days=1)))
                for d in YEAR_DAYS
            )
        ),
        "windows_tile_without_gap": bv.check(
            lambda: all(
                window.day_window(d)[1] == window.day_window(d + timedelta(days=1))[0]
                for d in YEAR_DAYS
            )
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
