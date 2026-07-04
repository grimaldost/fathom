"""Acceptance verifier for shipping-tax-small (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/checkout.py``) and the shipped suite
(``original/tests/``) — come from this task directory; identical for every arm, so reading
them leaks no scenario identity (ADR-0003). Emits a flat ``{criterion: bool}`` JSON and
exits 0 iff every criterion holds.

INTERDEPENDENCE task: the correct total needs the configured free-shipping threshold +
fee (one contract module) AND the tax rate (a second contract module). A fix that uses
only one contract passes one hard criterion and fails the other; both pass only when both
contracts are read and used. The matched ``-large`` twin buries those two modules among
~40 import-coherent siblings, so only the navigable volume differs.
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "shopcart"
MODULE = "checkout.py"
BUGGY_ORIGINAL = HERE / "original" / "checkout.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _checkout(view: Path):
    return bv.import_candidate(view, "shopcart.checkout", PACKAGE)


def _free_shipping_above_threshold(view: Path) -> bool:
    """At a subtotal above the configured threshold, no shipping fee + correct tax."""
    mod = _checkout(view)
    if mod is None or not hasattr(mod, "grand_total"):
        return False
    try:
        return mod.grand_total(Decimal("60")) == Decimal("64.80")
    except Exception:
        return False


def _charges_below_threshold_correctly(view: Path) -> bool:
    """Below the threshold: the configured shipping fee + correct tax (defeats a tax-only fix)."""
    mod = _checkout(view)
    if mod is None or not hasattr(mod, "grand_total"):
        return False
    try:
        return mod.grand_total(Decimal("40")) == Decimal("48.19")
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "free_shipping_above_threshold": _free_shipping_above_threshold(view),
        "charges_below_threshold_correctly": _charges_below_threshold_correctly(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
