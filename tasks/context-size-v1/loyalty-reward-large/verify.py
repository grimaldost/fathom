"""Acceptance verifier for loyalty-reward-small (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/points.py``) and the shipped suite
(``original/tests/``) — come from this task directory; identical for every arm, so reading
them leaks no scenario identity (ADR-0003). Emits a flat ``{criterion: bool}`` JSON and
exits 0 iff every criterion holds.

INTERDEPENDENCE task: the correct reward needs the customer's loyalty tier (one contract
module, ``accounts.tier_of``) AND that tier's configured rate (a second contract module,
``loyalty.rate_for``). A fix that uses only one contract — or hardcodes a single tier —
passes one hard criterion and fails the other; both pass only when both contracts are read
and used. The matched ``-large`` twin buries those two modules among ~40 import-coherent
siblings, so only the navigable volume differs.
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "rewards"
MODULE = "points.py"
BUGGY_ORIGINAL = HERE / "original" / "points.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _points(view: Path):
    return bv.import_candidate(view, "rewards.points", PACKAGE)


def _reward_reflects_gold_tier(view: Path) -> bool:
    """A gold customer earns the gold rate (2%), not the silver/flat base rate."""
    mod = _points(view)
    if mod is None or not hasattr(mod, "reward"):
        return False
    try:
        return mod.reward("c_gold", Decimal("100")) == Decimal("2.00")
    except Exception:
        return False


def _reward_reflects_platinum_tier(view: Path) -> bool:
    """A platinum customer earns the platinum rate (5%) — a second tier defeats a hardcode."""
    mod = _points(view)
    if mod is None or not hasattr(mod, "reward"):
        return False
    try:
        return mod.reward("c_plat", Decimal("100")) == Decimal("5.00")
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "reward_reflects_gold_tier": _reward_reflects_gold_tier(view),
        "reward_reflects_platinum_tier": _reward_reflects_platinum_tier(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
