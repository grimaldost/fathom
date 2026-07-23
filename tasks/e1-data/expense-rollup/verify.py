"""Acceptance verifier for expense-rollup (harness-side, scenario-blind).

Reads ONLY the result-view path in argv[1]. Locates the candidate's (possibly
edited or renamed) rollup module, imports it, and runs its `summarize` function
against a CANONICAL set of transaction rows that includes two uncategorized
(blank-category) rows -- the subtle case. The correct summary buckets those rows
so the category breakdown accounts for every amount and the grand total matches
the raw input; a naive fix that only patches the grand total (or keeps dropping
the blank rows) leaves the breakdown short and fails the subtle case while still
passing the easy, fully-categorized rows.

Emits a single {criterion: bool} JSON object; exits 0 iff
`output_correct_on_subtle_case`. Fails closed on any error and restores
sys.path / sys.modules after importing candidate code.
"""

import importlib.util
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Canonical input -- carried by the verifier so the subtle (blank-category) rows
# are always present regardless of what the candidate did to the input file.
CANONICAL_ROWS = [
    {"id": "1", "category": "groceries", "amount": "20.00"},
    {"id": "2", "category": "transport", "amount": "5.50"},
    {"id": "3", "category": "groceries", "amount": "15.25"},
    {"id": "4", "category": "", "amount": "8.00"},
    {"id": "5", "category": "dining", "amount": "12.00"},
    {"id": "6", "category": "transport", "amount": "3.50"},
    {"id": "7", "category": "", "amount": "4.00"},
]

# Easy rows: the fully-categorized buckets. Correct even for a naive fix.
EASY_EXPECTED = {
    "groceries": Decimal("35.25"),
    "transport": Decimal("9.00"),
    "dining": Decimal("12.00"),
}
# Subtle case: every amount (including the two blank-category rows) is accounted
# for, so the breakdown sums to the true grand total and the grand total agrees.
TRUE_GRAND_TOTAL = Decimal("68.25")


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _find_module(view):
    """Return the path of the candidate .py file that defines `summarize`."""
    preferred = view / "rollup.py"
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
        if "def summarize" in text:
            return path
    return None


def _load_summarize(view):
    mod_path = _find_module(view)
    if mod_path is None:
        return None, None
    name = "_candidate_rollup"
    saved = sys.modules.get(name)
    saved_path = list(sys.path)
    sys.path.insert(0, str(mod_path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, mod_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        func = getattr(module, "summarize", None)
        return func, module
    except Exception:
        return None, None
    finally:
        if saved is not None:
            sys.modules[name] = saved
        else:
            sys.modules.pop(name, None)
        sys.path[:] = saved_path


def _breakdown_from_result(result):
    """Coerce a summarize() result into (by_category dict, grand_total)."""
    if not isinstance(result, dict):
        return None, None
    raw_cats = result.get("by_category")
    if not isinstance(raw_cats, dict):
        return None, None
    by_category = {}
    for name, total in raw_cats.items():
        dec = _to_decimal(total)
        if dec is None:
            return None, None
        by_category[str(name)] = dec
    grand = _to_decimal(result.get("grand_total"))
    return by_category, grand


def _breakdown_from_output_file(view):
    """Fallback: parse a candidate-produced summary.json if the function moved."""
    for path in sorted(view.rglob("summary.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        by_category, grand = _breakdown_from_result(data)
        if by_category is not None:
            return by_category, grand
    return None, None


def _evaluate(by_category, grand_total):
    easy_ok = all(by_category.get(name) == expected for name, expected in EASY_EXPECTED.items())
    breakdown_sum = sum(by_category.values(), Decimal("0"))
    subtle_ok = grand_total == TRUE_GRAND_TOTAL and breakdown_sum == TRUE_GRAND_TOTAL
    return easy_ok, subtle_ok


def main():
    result = {
        "output_correct_on_subtle_case": False,
        "output_correct_on_easy_case": False,
    }
    if len(sys.argv) != 2:
        print(json.dumps(result, sort_keys=True))
        return 1

    view = Path(sys.argv[1])
    by_category = grand_total = None
    try:
        func, _ = _load_summarize(view)
        if func is not None:
            by_category, grand_total = _breakdown_from_result(func(list(CANONICAL_ROWS)))
        if by_category is None:
            by_category, grand_total = _breakdown_from_output_file(view)
    except Exception:
        by_category = grand_total = None

    if by_category is not None and grand_total is not None:
        easy_ok, subtle_ok = _evaluate(by_category, grand_total)
        result["output_correct_on_easy_case"] = bool(easy_ok)
        result["output_correct_on_subtle_case"] = bool(subtle_ok)

    print(json.dumps(result, sort_keys=True))
    return 0 if result["output_correct_on_subtle_case"] else 1


if __name__ == "__main__":
    sys.exit(main())
