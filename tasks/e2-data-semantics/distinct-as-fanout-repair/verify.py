"""Blind verifier for distinct-as-fanout-repair.

Reads ONLY argv[1] (the result-view path). Runs the candidate's
`revenue_by_category` against a CANONICAL order ledger and product lookup carried
by this file.

The trap: `product_lookup` is grained on (product_id, effective_from), so joining
on product_id alone fans a recategorised product's orders across both of its
lookup rows. The first repair that presents itself is to count each order once --
which restores the row count and the grand total, and lands the recategorised
product's revenue in whichever lookup row was read first (the retired category).

- easy   `total_revenue_correct` -- the grand total equals the ledger's own sum.
  Counting each order once satisfies this.
- subtle `measure_correct_after_fix` -- the per-category measure matches the
  known-good, which needs the lookup row in force ON THE ORDER DATE.

Fails closed on any error.
"""

import importlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

CANONICAL_LOOKUP = [
    {"product_id": "Q1", "category": "tools", "effective_from": "2025-01-01"},
    {"product_id": "Q2", "category": "outdoor", "effective_from": "2025-01-01"},
    {"product_id": "Q2", "category": "indoor", "effective_from": "2026-01-15"},
    {"product_id": "Q3", "category": "indoor", "effective_from": "2025-01-01"},
    {"product_id": "Q4", "category": "tools", "effective_from": "2025-01-01"},
]

CANONICAL_ORDERS = [
    {"order_id": "N1", "product_id": "Q1", "order_date": "2026-04-01", "amount": "200.00"},
    {"order_id": "N2", "product_id": "Q2", "order_date": "2026-04-01", "amount": "60.00"},
    {"order_id": "N3", "product_id": "Q2", "order_date": "2026-04-02", "amount": "40.00"},
    {"order_id": "N4", "product_id": "Q3", "order_date": "2026-04-02", "amount": "15.00"},
    {"order_id": "N5", "product_id": "Q3", "order_date": "2026-04-02", "amount": "15.00"},
    {"order_id": "N6", "product_id": "Q4", "order_date": "2026-04-03", "amount": "70.00"},
    {"order_id": "N7", "product_id": "Q4", "order_date": "2026-04-03", "amount": "70.00"},
    # Placed before Q2 was recategorised, so it belongs to the OLD category.
    {"order_id": "N8", "product_id": "Q2", "order_date": "2025-06-01", "amount": "25.00"},
]

LEDGER_TOTAL = Decimal("495.00")
KNOWN_GOOD = {
    "tools": Decimal("340.00"),
    "indoor": Decimal("130.00"),
    "outdoor": Decimal("25.00"),
}

CRITERIA = ("total_revenue_correct", "measure_correct_after_fix")
GATE = "measure_correct_after_fix"


def _load_func(view, hint, dotted, func_name):
    saved_path = list(sys.path)
    saved_modules = dict(sys.modules)
    sys.path.insert(0, str(view))
    try:
        try:
            attr = getattr(importlib.import_module(dotted), func_name, None)
            if callable(attr):
                return attr
        except Exception:
            pass
        preferred = view / hint
        candidates = [preferred] if preferred.is_file() else []
        candidates += [
            p
            for p in sorted(view.rglob("*.py"))
            if p != preferred and p.name != "verify.py" and "test" not in p.name.lower()
        ]
        for path in candidates:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if f"def {func_name}(" not in text:
                continue
            try:
                rel = path.relative_to(view).with_suffix("")
                attr = getattr(importlib.import_module(".".join(rel.parts)), func_name, None)
            except Exception:
                continue
            if callable(attr):
                return attr
        return None
    finally:
        sys.path[:] = saved_path
        sys.modules.clear()
        sys.modules.update(saved_modules)


def _decimals(mapping):
    """Non-zero entries of *mapping* as Decimals, or None if anything is unusable."""
    out = {}
    for key, value in mapping.items():
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None
        if amount != 0:
            out[str(key)] = amount
    return out


def main():
    result = dict.fromkeys(CRITERIA, False)
    if len(sys.argv) != 2:
        print(json.dumps(result, sort_keys=True))
        return 1

    view = Path(sys.argv[1])
    try:
        func = _load_func(view, "category_report.py", "category_report", "revenue_by_category")
        if func is not None:
            produced = func(
                [dict(row) for row in CANONICAL_ORDERS],
                [dict(row) for row in CANONICAL_LOOKUP],
            )
            totals = _decimals(produced) if isinstance(produced, dict) else None
            if totals is not None:
                result["total_revenue_correct"] = sum(totals.values()) == LEDGER_TOTAL
                result["measure_correct_after_fix"] = totals == KNOWN_GOOD
    except Exception:
        pass

    print(json.dumps(result, sort_keys=True))
    return 0 if result[GATE] else 1


if __name__ == "__main__":
    sys.exit(main())
