"""Acceptance verifier for fix-clamp2 (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/core.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003).

The bank's weak-floor anchor: a single missing branch in a single function. Every
tier is expected to pass, which is the point — it anchors the bottom of the ladder
and shows the instrument is not manufacturing failures.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates
on ``standard`` only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "rangekit"
MODULE = "core.py"
BUGGY_ORIGINAL = HERE / "original" / "core.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "clamp_in_range",
    "clamp_below_reported",
    "clamp_below_general",
    "clamp_above_preserved",
    "clamp_two_sided_general",
    "no_regression",
    "regression_test_present",
]

GRID = [
    (-7, 0, 10),
    (-1, 2, 8),
    (0, 0, 0),
    (3, 5, 5),
    (5, 0, 10),
    (11, 0, 10),
    (2.5, 0, 10),
    (-0.5, 0.0, 1.0),
    (7.25, 7.25, 9.0),
]


def _clamp(view: Path):
    mod = bv.import_candidate(view, "rangekit.core", PACKAGE)
    if mod is None or not hasattr(mod, "clamp"):
        return None
    return mod.clamp


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])
    clamp = _clamp(view)

    results = {
        # --- thin: the anchor plus the symptom the instruction names -------------
        "clamp_in_range": bv.check(lambda: clamp(5, 0, 10) == 5),
        "clamp_below_reported": bv.check(lambda: clamp(-5, 0, 10) == 0),
        # --- standard: the bound must hold generally, and the other bound must
        #     still hold (a one-sided rewrite trips this) -------------------------
        "clamp_below_general": bv.check(lambda: clamp(-1, 2, 8) == 2 and clamp(3, 5, 5) == 5),
        "clamp_above_preserved": bv.check(lambda: clamp(20, 0, 10) == 10 and clamp(9, 5, 5) == 5),
        # The capability-gated criterion of this task, and the reason it exists:
        # `clamp_below_general` alone is satisfied by a one-sided rewrite, and
        # `clamp_above_preserved` alone is satisfied by the untouched buggy source.
        # Requiring BOTH bounds at once on inputs the instruction never names is
        # false at the starting state AND false for a patch that trades one bound
        # for the other, while any correct clamp satisfies it.
        "clamp_two_sided_general": bv.check(
            lambda: (
                clamp(-1, 2, 8) == 2
                and clamp(20, 0, 10) == 10
                and clamp(3, 5, 5) == 5
                and clamp(9, 5, 5) == 5
            )
        ),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: an independent property sweep over inputs the instruction
        #     never names — value identity for floats, and the two defining
        #     properties of a clamp (boundedness + idempotence) --------------------
        "clamp_float_exact": bv.check(
            lambda: (
                clamp(2.5, 0, 10) == 2.5
                and isinstance(clamp(2.5, 0, 10), float)
                and clamp(-0.5, 0.0, 1.0) == 0.0
            )
        ),
        "clamp_bounded_and_idempotent": bv.check(
            lambda: all(
                low <= clamp(v, low, high) <= high
                and clamp(clamp(v, low, high), low, high) == clamp(v, low, high)
                for v, low, high in GRID
            )
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
