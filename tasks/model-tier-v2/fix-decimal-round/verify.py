"""Acceptance verifier for fix-decimal-round (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/fast.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003).

Backend parity. The instruction names two positive values. The obvious float fix,
``floor(value * 10**places + 0.5)``, gets both of them right and rounds every
negative tie the wrong way — the standard oracle sits on the negatives and on a
parity grid of binary-exact values. The strong oracle sits on values that a float
cannot hold exactly (``2.675``, ``1.005``, ``8.615``): a fix built on
``Decimal(value)`` rather than ``Decimal(str(value))`` inherits the float's error and
diverges from the exact backend there, and on the ``total`` consumer, which the
instruction never mentions.

The expected answers are computed here with ``decimal``, not read from the
candidate's ``exact`` module, so a candidate that "fixes" the parity by breaking the
exact backend gains nothing.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates
on ``standard`` only.
"""

import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "money"
MODULE = "fast.py"
BUGGY_ORIGINAL = HERE / "original" / "fast.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "fast_no_tie",
    "fast_half_up_reported",
    "fast_half_up_negative",
    "backend_parity_binary_grid",
    "no_regression",
    "regression_test_present",
]

# Binary-exact values (eighths): every one of them is representable as a float, so
# the two backends must agree on them without any float-precision argument.
BINARY_GRID = [k / 8 for k in range(-40, 41)]
BINARY_PLACES = (0, 1, 2, 3)

# Decimal literals a float CANNOT hold exactly. The documented rule is about the
# value the caller wrote, so these must round the same way in both backends.
DECIMAL_LITERALS = (2.675, 1.005, 8.615, 0.615, -2.675, -1.005, 1.115)

LINE_ITEMS = ((1, 2.675), (1, 1.005), (3, 0.415), (2, 0.125), (7, 1.115))


def expected(value: float, places: int = 0) -> float:
    """Half-away-from-zero rounding of the value the caller wrote."""
    quantum = Decimal(1).scaleb(-places)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])
    fast = bv.import_candidate(view, "money.fast", PACKAGE)
    total = bv.import_candidate(view, "money.total", PACKAGE)

    results = {
        # --- thin: the anchor plus the two values the instruction names -----------
        "fast_no_tie": bv.check(
            lambda: (
                fast.round_half_up(2.4) == 2.0
                and fast.round_half_up(2.6) == 3.0
                and fast.round_half_up(2.34, 2) == 2.34
            )
        ),
        "fast_half_up_reported": bv.check(
            lambda: fast.round_half_up(0.5) == 1.0 and fast.round_half_up(0.125, 2) == 0.13
        ),
        # --- standard: the same rule on the other side of zero, and parity over a
        #     grid the instruction never names -------------------------------------
        "fast_half_up_negative": bv.check(
            lambda: (
                fast.round_half_up(-0.5) == -1.0
                and fast.round_half_up(-2.5) == -3.0
                and fast.round_half_up(-0.125, 2) == -0.13
            )
        ),
        "backend_parity_binary_grid": bv.check(
            lambda: all(
                fast.round_half_up(v, p) == expected(v, p)
                for v in BINARY_GRID
                for p in BINARY_PLACES
            )
        ),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: values a float cannot hold exactly, and the order-line
        #     consumer — neither is named in the instruction ----------------------
        "backend_parity_decimal_literals": bv.check(
            lambda: all(fast.round_half_up(v, 2) == expected(v, 2) for v in DECIMAL_LITERALS)
        ),
        "parity_through_line_total": bv.check(
            lambda: all(
                total.line_total(q, p, "fast") == total.line_total(q, p, "exact")
                for q, p in LINE_ITEMS
            )
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
