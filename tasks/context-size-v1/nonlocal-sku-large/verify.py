"""Acceptance verifier for nonlocal-sku-small (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/keys.py``) and the shipped suite
(``original/tests/``) — come from this task directory; identical for every arm, so reading
them leaks no scenario identity (ADR-0003). Emits a flat ``{criterion: bool}`` JSON and
exits 0 iff every criterion holds.

INTERDEPENDENCE task: the buggy ``keys.sku_key`` is the shared root helper imported by two
callers (``inventory.stock_for`` and ``pricing.price_for``). The correct fix routes that
root through the canonical aliasing contract (``aliases.canonical``); both callers then
merge a product's code variants. A band-aid in one caller passes that caller's criterion
and fails the other; both pass only when the shared root is fixed. The matched ``-large``
twin buries these modules among ~40 import-coherent siblings, so only the navigable volume
differs.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "warehouse"
MODULE = "keys.py"
BUGGY_ORIGINAL = HERE / "original" / "keys.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _stock_merges_aliases(view: Path) -> bool:
    """Stock totals merge a product's code variants (alias root fixed)."""
    mod = bv.import_candidate(view, "warehouse.inventory", PACKAGE)
    if mod is None or not hasattr(mod, "stock_for"):
        return False
    try:
        ledger = [("WIDGET", 3), ("WID", 2), ("WIDGET-V2", 1)]
        return mod.stock_for("WIDGET", ledger) == 6
    except Exception:
        return False


def _price_merges_aliases(view: Path) -> bool:
    """A price lookup by a variant code resolves to the canonical product (defeats a one-caller fix)."""
    mod = bv.import_candidate(view, "warehouse.pricing", PACKAGE)
    if mod is None or not hasattr(mod, "price_for"):
        return False
    try:
        return mod.price_for("WID", {"WIDGET": 999}) == 999
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "stock_merges_aliases": _stock_merges_aliases(view),
        "price_merges_aliases": _price_merges_aliases(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
