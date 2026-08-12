"""Acceptance verifier for feature-ndjson-merge (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/merge.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003).

Shared-helper fan-out. The documented merge rule has three entry points; the
instruction names one of them (``merge_text``). ``merge_lines`` carries its own copy
of the concatenation loop, so a fix written inside ``merge_text`` leaves it wrong —
the standard oracle sits there. ``merge_records`` is the shared entry point both
should be routed through; the strong oracle sits there, plus a parity check across
all three paths.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates
on ``standard`` only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "ndj"
MODULE = "merge.py"
BUGGY_ORIGINAL = HERE / "original" / "merge.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "merge_text_disjoint",
    "merge_text_dedupes",
    "merge_lines_dedupes",
    "merge_lines_position_preserved",
    "no_regression",
    "regression_test_present",
]

# Disjoint ids — nothing to replace.
L_DISJOINT = '{"id": "a", "v": 1}\n{"id": "b", "v": 2}\n'
R_DISJOINT = '{"id": "c", "v": 3}\n'
EXPECT_DISJOINT = [{"id": "a", "v": 1}, {"id": "b", "v": 2}, {"id": "c", "v": 3}]

# The reported shape: one shared id, right wins.
L_SIMPLE = '{"id": "a", "v": 1}\n'
R_SIMPLE = '{"id": "a", "v": 9}\n'
EXPECT_SIMPLE = [{"id": "a", "v": 9}]

# Replacements arriving out of order — the replacement keeps the REPLACED record's
# position, so the result is not simply "left, then the new right records".
L_ORDER = '{"id": "a", "v": 1}\n{"id": "b", "v": 2}\n{"id": "c", "v": 3}\n'
R_ORDER = '{"id": "c", "v": 30}\n{"id": "a", "v": 10}\n{"id": "d", "v": 4}\n'
EXPECT_ORDER = [
    {"id": "a", "v": 10},
    {"id": "b", "v": 2},
    {"id": "c", "v": 30},
    {"id": "d", "v": 4},
]


def _merge(view: Path):
    return bv.import_candidate(view, "ndj.merge", PACKAGE)


def _records(text):
    import json

    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])
    mod = _merge(view)

    results = {
        # --- thin: the anchor plus the case the instruction names ----------------
        "merge_text_disjoint": bv.check(
            lambda: mod.merge_text(L_DISJOINT, R_DISJOINT) == EXPECT_DISJOINT
        ),
        "merge_text_dedupes": bv.check(lambda: mod.merge_text(L_SIMPLE, R_SIMPLE) == EXPECT_SIMPLE),
        # --- standard: the same rule through the line source, which the
        #     instruction never names ---------------------------------------------
        "merge_lines_dedupes": bv.check(
            lambda: mod.merge_lines(L_SIMPLE.splitlines(), R_SIMPLE.splitlines()) == EXPECT_SIMPLE
        ),
        "merge_lines_position_preserved": bv.check(
            lambda: mod.merge_lines(L_ORDER.splitlines(), R_ORDER.splitlines()) == EXPECT_ORDER
        ),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: the shared entry point itself, and parity across all three
        #     documented paths — neither is named in the instruction ---------------
        "merge_records_dedupes": bv.check(
            lambda: mod.merge_records(_records(L_ORDER), _records(R_ORDER)) == EXPECT_ORDER
        ),
        "merge_all_paths_agree": bv.check(
            lambda: (
                mod.merge_text(L_ORDER, R_ORDER)
                == mod.merge_lines(L_ORDER.splitlines(), R_ORDER.splitlines())
                == mod.merge_records(_records(L_ORDER), _records(R_ORDER))
                == EXPECT_ORDER
            )
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
