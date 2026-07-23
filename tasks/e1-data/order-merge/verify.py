"""Acceptance verifier for order-merge (harness-side, scenario-blind).

Reads ONLY the result-view path in argv[1]. Locates the candidate's (possibly
edited or renamed) enrich module, imports it, and runs its `revenue_by_region`
function against a CANONICAL orders + customers pair. The customer table carries
a duplicate lookup row for one customer (C2, South) -- the subtle case. A join
that fans out over the duplicate double-counts that customer's orders, inflating
one region's revenue. The correct fix deduplicates the lookup so each order is
counted once; a naive fix (e.g. deduplicating the already-unique orders) leaves
the fan-out and fails the subtle region while the untouched region stays correct.

Emits a single {criterion: bool} JSON object; exits 0 iff
`output_correct_on_subtle_case`. Fails closed on any error and restores
sys.path / sys.modules after importing candidate code.
"""

import importlib.util
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Canonical input -- carried by the verifier. customers has a duplicate row for
# C2 (the subtle case); orders are all unique.
CANONICAL_ORDERS = [
    {"order_id": "O1", "customer_id": "C1", "amount": "100.00"},
    {"order_id": "O2", "customer_id": "C2", "amount": "50.00"},
    {"order_id": "O3", "customer_id": "C3", "amount": "30.00"},
    {"order_id": "O4", "customer_id": "C2", "amount": "20.00"},
    {"order_id": "O5", "customer_id": "C1", "amount": "40.00"},
]
CANONICAL_CUSTOMERS = [
    {"customer_id": "C1", "region": "North"},
    {"customer_id": "C2", "region": "South"},
    {"customer_id": "C3", "region": "North"},
    {"customer_id": "C2", "region": "South"},
]

# Easy case: North's customers (C1, C3) each appear once in the lookup, so North
# is correct even with the fan-out bug. Subtle case: South is only correct when
# the duplicate C2 lookup row is not double-counted.
EASY_REGION = "North"
EASY_EXPECTED = Decimal("170.00")
SUBTLE_REGION = "South"
SUBTLE_EXPECTED = Decimal("70.00")


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _find_module(view):
    """Return the path of the candidate .py file that defines `revenue_by_region`."""
    preferred = view / "enrich.py"
    candidates = []
    if preferred.is_file():
        candidates.append(preferred)
    for path in sorted(view.rglob("*.py")):
        if path.name == "verify.py" or "test" in path.name.lower():
            continue
        if path not in candidates:
            candidates.append(path)
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "def revenue_by_region" in text:
            return path
    return None


def _load_func(view):
    mod_path = _find_module(view)
    if mod_path is None:
        return None
    name = "_candidate_enrich"
    saved = sys.modules.get(name)
    saved_path = list(sys.path)
    sys.path.insert(0, str(mod_path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, mod_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return getattr(module, "revenue_by_region", None)
    except Exception:
        return None
    finally:
        if saved is not None:
            sys.modules[name] = saved
        else:
            sys.modules.pop(name, None)
        sys.path[:] = saved_path


def _totals_from_result(result):
    if not isinstance(result, dict):
        return None
    totals = {}
    for region, total in result.items():
        dec = _to_decimal(total)
        if dec is None:
            return None
        totals[str(region)] = dec
    return totals


def _totals_from_output_file(view):
    """Fallback: parse a candidate-produced revenue.json if the function moved."""
    for path in sorted(view.rglob("revenue.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        totals = _totals_from_result(data)
        if totals is not None:
            return totals
    return None


def main():
    result = {
        "output_correct_on_subtle_case": False,
        "output_correct_on_easy_case": False,
    }
    if len(sys.argv) != 2:
        print(json.dumps(result, sort_keys=True))
        return 1

    view = Path(sys.argv[1])
    totals = None
    try:
        func = _load_func(view)
        if func is not None:
            totals = _totals_from_result(func(list(CANONICAL_ORDERS), list(CANONICAL_CUSTOMERS)))
        if totals is None:
            totals = _totals_from_output_file(view)
    except Exception:
        totals = None

    if totals is not None:
        result["output_correct_on_easy_case"] = bool(totals.get(EASY_REGION) == EASY_EXPECTED)
        result["output_correct_on_subtle_case"] = bool(totals.get(SUBTLE_REGION) == SUBTLE_EXPECTED)

    print(json.dumps(result, sort_keys=True))
    return 0 if result["output_correct_on_subtle_case"] else 1


if __name__ == "__main__":
    sys.exit(main())
